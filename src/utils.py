import json
import os
import time
from pathlib import Path

STATE_FILE = "state.json"
OUTPUT_DIR = Path("output")

def ensure_output_dir():
    """Ensure output directory exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def has_session_state():
    """Check if the playwright state file exists."""
    return os.path.exists(STATE_FILE)

def get_auth_cookies_from_env():
    """Return auth cookies from environment if available."""
    auth_token = os.getenv("AUTH_TOKEN")
    ct0 = os.getenv("CT0")
    if auth_token and ct0:
        return [
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"}
        ]
    return None

def write_json(data, filepath):
    """Write data to a JSON file safely."""
    ensure_output_dir()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def read_json(filepath):
    """Read a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_text(text):
    """Clean extra spaces and normalizes text slightly."""
    if not text:
        return ""
    # We preserve newlines for readability, but trim surrounding space
    return text.strip()
