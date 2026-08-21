import time
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from src.utils import has_session_state, get_auth_cookies_from_env, clean_text, STATE_FILE
from bs4 import BeautifulSoup

console = Console()

class BrowserScraper:
    def __init__(self, headless=True):
        self.headless = headless

    def _setup_context(self, p):
        browser = p.chromium.launch(headless=self.headless)
        context_args = {
            "viewport": {'width': 1280, 'height': 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        if has_session_state():
            context = browser.new_context(storage_state=STATE_FILE, **context_args)
        else:
            context = browser.new_context(**context_args)
            cookies = get_auth_cookies_from_env()
            if cookies:
                context.add_cookies(cookies)

        return browser, context

    def login_interactive(self):
        """Open browser to let user log in manually and save state."""
        with sync_playwright() as p:
            # Must not be headless for manual login
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            console.print("[cyan]Opening X.com for login. Please log in to your account.[/cyan]")
            console.print("[cyan]Waiting for navigation to home page or bookmarks page...[/cyan]")

            page.goto("https://x.com/login")

            # Wait for user to successfully login and end up on the home page or some inner page
            try:
                # Wait for the main navigation element to appear (indicates successful login)
                page.wait_for_selector('[data-testid="AppTabBar_Home_Link"]', timeout=300000) # 5 minutes timeout
                console.print("[green]Login successful![/green]")

                # Save state
                context.storage_state(path=STATE_FILE)
                console.print(f"[green]Session saved to {STATE_FILE}. You can now use the 'scrape' command.[/green]")
            except PlaywrightTimeoutError:
                console.print("[red]Login timed out. Please try again.[/red]")
            finally:
                browser.close()

    def parse_tweet_dom(self, tweet_html):
        """Parse raw HTML of a single tweet using BeautifulSoup."""
        soup = BeautifulSoup(tweet_html, 'html.parser')

        # We need a robust way to extract. X DOM is heavily obfuscated.
        # But commonly:

        tweet_data = {
            "id": "unknown",
            "handle": "unknown",
            "display_name": "unknown",
            "timestamp": "unknown",
            "text": "",
            "urls": [],
            "quoted_handle": None,
            "quoted_text": None
        }

        # Find user info (handle, display name)
        # Typically under an anchor tag with User-Name
        user_info_tag = soup.find('div', {'data-testid': 'User-Name'})
        if user_info_tag:
            links = user_info_tag.find_all('a', href=True)
            if links:
                # First link is usually the display name + profile link
                profile_link = links[0].get('href', '')
                tweet_data["handle"] = profile_link.lstrip('/')

                spans = links[0].find_all('span')
                if spans:
                    tweet_data["display_name"] = spans[0].text

        # Find timestamp and ID
        time_tag = soup.find('time')
        if time_tag:
            tweet_data["timestamp"] = time_tag.get('datetime', 'unknown')
            parent_link = time_tag.find_parent('a')
            if parent_link and '/status/' in parent_link.get('href', ''):
                href = parent_link.get('href')
                tweet_data["id"] = href.split('/')[-1]

        # Text Content
        text_tag = soup.find('div', {'data-testid': 'tweetText'})
        if text_tag:
            tweet_data["text"] = clean_text(text_tag.get_text(separator='\n'))

            # Extract links within text
            links = text_tag.find_all('a', href=True)
            for link in links:
                href = link['href']
                if not href.startswith('/') and 't.co' not in href:
                    tweet_data["urls"].append(href)

        # URLs not in text (e.g., cards)
        card_tags = soup.find_all('div', {'data-testid': 'card.wrapper'})
        for card in card_tags:
            links = card.find_all('a', href=True)
            for link in links:
                 href = link['href']
                 if href.startswith('http') and href not in tweet_data["urls"]:
                      tweet_data["urls"].append(href)

        # Quoted tweet
        quoted_tag = soup.find('div', {'role': 'link', 'tabindex': '0'}) # This often wraps the quoted tweet
        # A more reliable way is to find a second set of User-Name or a div that looks like a quote,
        # but X DOM is tricky. Let's try to find an inner element that has 'dir' and looks like text
        # that isn't the main text.
        # Often quoted tweets have a distinct structure. Let's look for a second time element or user info

        # It's safer to extract it if we find multiple user infos
        all_user_infos = soup.find_all('div', {'data-testid': 'User-Name'})
        if len(all_user_infos) > 1:
            quoted_user_info = all_user_infos[1]
            links = quoted_user_info.find_all('a', href=True)
            if links:
                 quoted_profile_link = links[0].get('href', '')
                 tweet_data["quoted_handle"] = quoted_profile_link.lstrip('/')

            # Trying to find quoted text. It usually appears after the quoted user info.
            # This is brittle, so we just do our best.
            parent_div = quoted_user_info.find_parent('div')
            if parent_div:
                sibling_text = parent_div.find_next_sibling('div', {'dir': 'auto'})
                if sibling_text:
                     tweet_data["quoted_text"] = clean_text(sibling_text.get_text(separator='\n'))

        return tweet_data

    def _ensure_authenticated(self, page):
        """Check if we are actually logged in."""
        try:
             page.wait_for_selector('[data-testid="AppTabBar_Home_Link"]', timeout=10000)
             return True
        except PlaywrightTimeoutError:
             return False

    def scrape_bookmarks(self, limit=0, fetch_threads=False):
        """Scrape bookmarks from the timeline."""
        bookmarks = []
        seen_ids = set()

        with sync_playwright() as p:
            browser, context = self._setup_context(p)
            page = context.new_page()

            console.print("[cyan]Navigating to Bookmarks...[/cyan]")
            page.goto("https://x.com/i/bookmarks")

            if not self._ensure_authenticated(page):
                 console.print("[red]Authentication failed. Please run 'login' or check your .env cookies.[/red]")
                 browser.close()
                 return []

            console.print("[green]Authentication verified. Starting scrape...[/green]")

            try:
                # Wait for the first tweet to appear
                page.wait_for_selector('[data-testid="tweet"]', timeout=15000)

                scroll_attempts = 0
                max_scroll_attempts_without_new_data = 5

                with Progress() as progress:
                    task = progress.add_task("[cyan]Scraping bookmarks...", total=limit if limit > 0 else None)

                    while True:
                        tweet_elements = page.locator('[data-testid="tweet"]').all()
                        new_tweets_found = False

                        for elem in tweet_elements:
                            try:
                                html = elem.inner_html()
                                tweet_data = self.parse_tweet_dom(html)

                                # Only process if we found an ID and haven't seen it
                                if tweet_data["id"] != "unknown" and tweet_data["id"] not in seen_ids:
                                    seen_ids.add(tweet_data["id"])

                                    # Handle optional thread fetching
                                    if fetch_threads and tweet_data["id"] != "unknown":
                                        # Only fetch if it might be a thread. Opening a page takes time.
                                        # To fetch, we will pause our scraping loop, open a new context tab, fetch it, and close it.
                                        thread_page = context.new_page()
                                        try:
                                            # Wait briefly
                                            page.wait_for_timeout(500)
                                            thread_page.goto(f"https://x.com/x/status/{tweet_data['id']}")
                                            thread_page.wait_for_selector('[data-testid="tweet"]', timeout=10000)

                                            # We grab all tweets on this single page to enrich the text
                                            # A multi-tweet thread will render multiple articles
                                            articles = thread_page.locator('article').all()
                                            thread_texts = []

                                            for idx, article in enumerate(articles):
                                                try:
                                                    thread_html = article.inner_html()
                                                    thread_part_data = self.parse_tweet_dom(thread_html)
                                                    if thread_part_data["text"]:
                                                         prefix = "" if idx == 0 else "🧵 "
                                                         thread_texts.append(prefix + thread_part_data["text"])
                                                except Exception:
                                                    continue

                                            if len(thread_texts) > 1:
                                                # Replace main text with full thread
                                                tweet_data["text"] = "\n\n".join(thread_texts)

                                        except Exception as e:
                                            pass
                                        finally:
                                            thread_page.close()

                                    bookmarks.append(tweet_data)
                                    new_tweets_found = True
                                    progress.update(task, advance=1)

                                    if limit > 0 and len(bookmarks) >= limit:
                                        break
                            except Exception as e:
                                # Just skip failing elements
                                continue

                        if limit > 0 and len(bookmarks) >= limit:
                             console.print(f"\n[green]Reached limit of {limit} bookmarks.[/green]")
                             break

                        if not new_tweets_found:
                            scroll_attempts += 1
                            if scroll_attempts >= max_scroll_attempts_without_new_data:
                                console.print("\n[yellow]No new bookmarks found after several scrolls. Reached the end.[/yellow]")
                                break
                        else:
                            scroll_attempts = 0

                        # Scroll down
                        page.mouse.wheel(0, 2000)
                        page.wait_for_timeout(1500) # Wait for network

            except KeyboardInterrupt:
                 console.print("\n[yellow]Scraping interrupted by user. Saving progress...[/yellow]")
            except Exception as e:
                 console.print(f"\n[red]An error occurred: {e}[/red]")
            finally:
                 browser.close()

        return bookmarks

    def hydrate_tweets(self, tweet_ids):
        """Hydrate a list of tweet IDs by visiting their pages."""
        hydrated = []

        with sync_playwright() as p:
             browser, context = self._setup_context(p)
             page = context.new_page()

             # Navigate to home first to set cookies properly context
             page.goto("https://x.com/")
             if not self._ensure_authenticated(page):
                 console.print("[red]Authentication failed. Please run 'login' or check your .env cookies.[/red]")
                 browser.close()
                 return []

             try:
                 with Progress() as progress:
                     task = progress.add_task("[cyan]Hydrating tweets...", total=len(tweet_ids))

                     for i, tweet_id in enumerate(tweet_ids):
                         try:
                             # Use an arbitrary handle (x will redirect to the correct one)
                             page.goto(f"https://x.com/x/status/{tweet_id}")
                             page.wait_for_selector('[data-testid="tweet"]', timeout=10000)

                             # Let's wait a bit for it to settle
                             page.wait_for_timeout(1000)

                             html = page.locator('article').first.inner_html()
                             tweet_data = self.parse_tweet_dom(html)

                             # Ensure we assign the correct ID since the parser might fail if the URL wasn't found in a time tag
                             tweet_data["id"] = tweet_id
                             hydrated.append(tweet_data)

                         except Exception as e:
                             console.print(f"\n[yellow]Failed to hydrate tweet {tweet_id}: {e}[/yellow]")

                         progress.update(task, advance=1)
                         # Rate limit ourselves slightly to avoid bans
                         page.wait_for_timeout(1000)
             except KeyboardInterrupt:
                 console.print("\n[yellow]Hydration interrupted by user. Saving progress...[/yellow]")
             finally:
                 browser.close()

        return hydrated
