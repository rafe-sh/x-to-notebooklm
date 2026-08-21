import click
import os
from dotenv import load_dotenv
from rich.console import Console

from src.browser_scraper import BrowserScraper
from src.archive_parser import extract_tweet_ids_from_archive
from src.formatter import bundle_bookmarks

# Load environment variables
load_dotenv()
console = Console()

@click.group()
def cli():
    """X-to-NotebookLM Bookmark Bundler.
    Extract your X bookmarks and bundle them for Google NotebookLM."""
    pass

@cli.command()
def login():
    """Launch an interactive browser to log into X and save session state."""
    console.print("[bold]Launching interactive login...[/bold]")
    scraper = BrowserScraper(headless=False)
    scraper.login_interactive()

@cli.command()
@click.option('--limit', default=0, type=int, help="Maximum number of bookmarks to scrape (0 for no limit).")
@click.option('--fetch-threads', is_flag=True, help="Optional: navigate to fetch deep thread context.")
@click.option('--single-file', is_flag=True, help="Bundle all bookmarks into a single master markdown file.")
@click.option('--bundle-size', default=100, type=int, help="Number of bookmarks per markdown bundle chunk.")
def scrape(limit, fetch_threads, single_file, bundle_size):
    """Scrape bookmarks from your live X account and bundle them."""
    console.print("[bold cyan]Starting Live Scrape Mode[/bold cyan]")

    scraper = BrowserScraper(headless=True)
    bookmarks = scraper.scrape_bookmarks(limit=limit, fetch_threads=fetch_threads)

    if not bookmarks:
        console.print("[yellow]No bookmarks found or extraction failed.[/yellow]")
        return

    console.print(f"[green]Extracted {len(bookmarks)} bookmarks. Starting bundler...[/green]")
    bundle_bookmarks(bookmarks, "output", single_file=single_file, bundle_size=bundle_size)

@cli.command()
@click.option('--path', required=True, type=click.Path(exists=True), help="Path to your bookmarks.js or JSON file.")
@click.option('--single-file', is_flag=True, help="Bundle all bookmarks into a single master markdown file.")
@click.option('--bundle-size', default=100, type=int, help="Number of bookmarks per markdown bundle chunk.")
def parse_archive(path, single_file, bundle_size):
    """Parse an offline X data archive and hydrate tweets via browser."""
    console.print(f"[bold cyan]Starting Archive Parser Mode for: {path}[/bold cyan]")

    try:
        tweet_ids = extract_tweet_ids_from_archive(path)
    except Exception as e:
        console.print(f"[bold red]Failed to parse archive:[/bold red] {e}")
        return

    if not tweet_ids:
         console.print("[yellow]No tweet IDs found in the archive.[/yellow]")
         return

    console.print(f"[green]Found {len(tweet_ids)} tweet IDs. Starting hydration process...[/green]")

    scraper = BrowserScraper(headless=True)
    hydrated_bookmarks = scraper.hydrate_tweets(tweet_ids)

    if not hydrated_bookmarks:
         console.print("[yellow]Hydration yielded no results.[/yellow]")
         return

    console.print(f"[green]Successfully hydrated {len(hydrated_bookmarks)} bookmarks. Starting bundler...[/green]")
    bundle_bookmarks(hydrated_bookmarks, "output", single_file=single_file, bundle_size=bundle_size)

if __name__ == '__main__':
    cli()
