import json
import re
from pathlib import Path

def extract_tweet_ids_from_archive(filepath: str):
    """
    Parse an X data archive file (bookmarks.js or JSON) and return a list of tweet IDs.

    The official bookmarks.js usually starts with something like:
    window.YTD.bookmarks.part0 = [ { "bookmark" : { "tweetId" : "123456789" } }, ... ]
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Archive file not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # If it's the JS file, we need to strip the variable assignment
    if path.suffix == '.js':
        # Find the first '[' which usually denotes the start of the JSON array
        start_idx = content.find('[')
        if start_idx != -1:
            json_str = content[start_idx:]
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON from JS file. Ensure the file format is standard. Error: {e}")
        else:
            raise ValueError("Could not find JSON array start '[' in the .js file.")
    else:
        # Standard JSON file
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
             raise ValueError(f"Failed to parse JSON file. Error: {e}")

    tweet_ids = []

    # Extract IDs based on common structure
    if isinstance(data, list):
        for item in data:
            if "bookmark" in item and "tweetId" in item["bookmark"]:
                tweet_ids.append(item["bookmark"]["tweetId"])
            elif "tweetId" in item:
                tweet_ids.append(item["tweetId"])
            elif "tweet" in item and "id" in item["tweet"]:
                tweet_ids.append(item["tweet"]["id"])

    if not tweet_ids:
         print("[!] Warning: No tweet IDs could be extracted. The file format might not be supported.")

    return tweet_ids
