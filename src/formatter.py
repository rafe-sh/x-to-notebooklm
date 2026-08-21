from datetime import datetime
from pathlib import Path

def format_tweet_markdown(tweet):
    """
    Format a single tweet object into a markdown block.

    Expected tweet keys:
    - id: str
    - handle: str
    - display_name: str
    - timestamp: str
    - text: str
    - urls: list[str] (extracted urls)
    - quoted_handle: str (optional)
    - quoted_text: str (optional)
    """
    handle = tweet.get("handle", "unknown")
    display_name = tweet.get("display_name", handle)
    timestamp = tweet.get("timestamp", "Unknown Date")
    tweet_id = tweet.get("id", "unknown_id")
    text = tweet.get("text", "")
    urls = tweet.get("urls", [])

    quoted_handle = tweet.get("quoted_handle")
    quoted_text = tweet.get("quoted_text")

    # Source link
    source_link = f"https://x.com/{handle}/status/{tweet_id}"

    md = [
        f"## Post by @{handle} — [{timestamp}]",
        f"- **Author:** {display_name} (@{handle})",
        f"- **Source Link:** [{source_link}]({source_link})"
    ]

    if urls:
        links_str = ", ".join([f"[Link {i+1}]({url})" for i, url in enumerate(urls)])
        md.append(f"- **Extracted URLs:** {links_str}")

    md.append("\n### Content")

    if text:
        # Quote block formatting for content
        formatted_text = "\n".join([f"> {line}" for line in text.split("\n")])
        md.append(formatted_text)
    else:
        md.append("> (No text content / Media only)")

    if quoted_handle and quoted_text:
        md.append("\n### Quoted Post")
        formatted_quoted_text = "\n".join([f"> {line}" for line in quoted_text.split("\n")])
        md.append(f"> **@{quoted_handle}**: \n{formatted_quoted_text}")

    md.append("\n---\n")
    return "\n".join(md)


def generate_manifest(output_dir: Path, total_tweets: int, file_count: int, start_time: str, end_time: str = None):
    """Generate a manifest.md file indexing the bundle."""
    if end_time is None:
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    manifest_lines = [
        "# X Bookmarks Archive — Manifest",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "## Summary",
        f"- **Total Bookmarks Extracted:** {total_tweets}",
        f"- **Total Bundle Files:** {file_count}",
        f"- **Start Time:** {start_time}",
        f"- **End Time:** {end_time}",
        "",
        "## Instructions for NotebookLM",
        "1. Open [Google NotebookLM](https://notebooklm.google.com/).",
        "2. Create a new notebook.",
        "3. Drag and drop the `.md` files from this directory into the NotebookLM sources pane.",
        "4. Start querying your bookmarks!"
    ]

    manifest_path = output_dir / "manifest.md"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(manifest_lines))

    return manifest_path

def bundle_bookmarks(bookmarks, output_dir_path: str, single_file: bool = False, bundle_size: int = 100):
    """
    Bundle a list of bookmarks into markdown files.
    """
    output_dir = Path(output_dir_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_time = timestamp_str

    def write_bundle(bundle_bookmarks, filename, index=None):
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            header = "# X Bookmarks Archive — Bundle"
            if index is not None:
                header += f" [{index}]"
            f.write(f"{header}\n*Generated: {timestamp_str} | Total Items: {len(bundle_bookmarks)}*\n\n---\n\n")

            for tweet in bundle_bookmarks:
                f.write(format_tweet_markdown(tweet))
                f.write("\n")
        return filepath

    files_created = 0
    if single_file:
        write_bundle(bookmarks, "bookmarks_all.md")
        files_created = 1
    else:
        # Chunk logic
        for i in range(0, len(bookmarks), bundle_size):
            chunk = bookmarks[i:i + bundle_size]
            chunk_idx = (i // bundle_size) + 1
            filename = f"bookmarks_bundle_{chunk_idx:02d}.md"
            write_bundle(chunk, filename, index=chunk_idx)
            files_created += 1

    generate_manifest(output_dir, len(bookmarks), files_created, start_time)
    print(f"[+] Successfully bundled {len(bookmarks)} bookmarks into {files_created} markdown files.")
