# X-to-NotebookLM Bookmark Bundler

A lightweight, local, zero-cost CLI tool that extracts all bookmarks from your X (Twitter) account and bundles them into structured Markdown files optimized specifically for ingestion into **Google NotebookLM**.

## Features

- **Dual Engine**: Scrape directly from your live X bookmarks or hydrate data from an official X data export.
- **Zero-AI / Zero-Cost**: Does not use paid LLMs to scrape. 100% deterministic local Python code.
- **NotebookLM Optimized**: Consolidates thousands of bookmarks into large Markdown chunks to bypass NotebookLM's 50-file limit.
- **Session Persistence**: Run an interactive login once, and perform subsequent scraping fully headless.
- **Graceful Failure**: Safely saves progress if rate limits are hit or the script is stopped.

## Setup Instructions

1. **Clone the repository and install dependencies:**
   Ensure you have Python 3.8+ installed.
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Login to X / Twitter:**
   Run the interactive login command. A Chromium window will open.
   Log into your X account and wait for the terminal to confirm the session was saved.
   ```bash
   python main.py login
   ```
   *(Alternative: If you prefer, copy `.env.example` to `.env` and provide your `auth_token` and `ct0` cookies manually).*

## Usage

### Mode 1: Live Scraping
Scrape directly from your live `https://x.com/i/bookmarks` timeline.

```bash
# Scrape all bookmarks in chunks of 100 (Default)
python main.py scrape

# Scrape only the latest 50 bookmarks into a single master file
python main.py scrape --limit 50 --single-file

# Enable deep thread fetching (will visit individual tweet pages, slightly slower)
python main.py scrape --fetch-threads
```

### Mode 2: Archive Parsing
Hydrate an official X data export `bookmarks.js` file.

```bash
python main.py parse-archive --path ./data/bookmarks.js --single-file
```

## Importing into NotebookLM

1. Wait for the CLI to finish running. Check the `./output` folder for your `.md` files.
2. Open [Google NotebookLM](https://notebooklm.google.com/).
3. Create a new notebook or open an existing one.
4. Drag and drop all `.md` files from the `./output` directory into the NotebookLM sources pane on the left.
5. That's it! NotebookLM will process your sources, and you can now start querying your organized bookmarks.

## Disclaimer
This tool uses web scraping. Please be mindful of X's rate limits. Do not use this tool to spam or aggressively hit X servers. Use it purely for personal archival purposes.
