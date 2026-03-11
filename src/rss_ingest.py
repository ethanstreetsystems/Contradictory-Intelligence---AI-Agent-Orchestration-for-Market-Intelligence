from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from xml.etree import ElementTree as ET

import feedparser
import requests
import trafilatura


# -----------------------------
# Config
# -----------------------------

RSS_FEEDS = [
    {
        "source": "Import AI",
        "url": "https://importai.substack.com/feed",
    },
    {
        "source": "Peter Diamandis",
        "url": "https://www.diamandis.com/blog/rss.xml",
    }
]

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "rss_items.json"

REQUEST_TIMEOUT_SECONDS = 20
MAX_ITEMS_PER_FEED = 10
MIN_SUCCESS_WORD_COUNT = 200

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


# -----------------------------
# Basic helpers
# -----------------------------

def utc_now_iso() -> str:
    """Return the current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def ensure_data_dir() -> None:
    """Create the data directory if it does not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def safe_strip(value: Any) -> str:
    """Return a stripped string, or an empty string if the value is not a string."""
    if isinstance(value, str):
        return value.strip()
    return ""


def normalize_whitespace(text: str) -> str:
    """
    Do light cleanup so saved text is readable.
    This is basic sanitation, not enrichment.
    """
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def remove_html_tags(text: str) -> str:
    """Remove basic HTML tags from a string."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(re.findall(r"\b\w+\b", text))


# -----------------------------
# File loading / saving
# -----------------------------

def load_existing_items() -> List[Dict[str, Any]]:
    """Load existing items from rss_items.json if it exists."""
    if not OUTPUT_FILE.exists():
        return []

    try:
        with OUTPUT_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        print("Warning: rss_items.json is not a list. Starting with an empty list.")
        return []

    except json.JSONDecodeError:
        print("Warning: rss_items.json is invalid JSON. Starting with an empty list.")
        return []


def save_items(items: List[Dict[str, Any]]) -> None:
    """Save items to rss_items.json."""
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(items, file, indent=2, ensure_ascii=False)


def build_existing_link_set(items: List[Dict[str, Any]]) -> Set[str]:
    """Build a set of existing links so we can deduplicate new feed items."""
    existing_links: Set[str] = set()

    for item in items:
        link = safe_strip(item.get("link"))
        if link:
            existing_links.add(link)

    return existing_links


# -----------------------------
# Article fetch and extraction
# -----------------------------

def download_article_html(url: str) -> str:
    """Download the raw HTML for an article page."""
    response = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text


def parse_trafilatura_xml(xml_text: str) -> Dict[str, str]:
    """
    Parse trafilatura XML output and return:
    - article_text
    - author
    - language

    author and language are optional.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {
            "article_text": "",
            "author": "",
            "language": "",
        }

    author = ""
    language = ""

    for element in root.iter():
        if not author:
            author = safe_strip(element.attrib.get("author"))
        if not language:
            language = safe_strip(element.attrib.get("language"))

    body = root.find(".//main")
    if body is None:
        body = root.find(".//body")

    text_parts: List[str] = []

    if body is not None:
        for element in body.iter():
            if element.text and element.text.strip():
                text_parts.append(element.text.strip())
    else:
        for element in root.iter():
            if element.text and element.text.strip():
                text_parts.append(element.text.strip())

    article_text = normalize_whitespace("\n\n".join(text_parts))

    return {
        "article_text": article_text,
        "author": author,
        "language": language,
    }


def extract_article_data_from_html(html: str, url: str) -> Dict[str, str]:
    """
    Extract article text and optional metadata from HTML using trafilatura.
    """
    xml_output = trafilatura.extract(
        html,
        url=url,
        output_format="xml",
        with_metadata=True,
        include_comments=False,
        include_tables=False,
        include_links=False,
        favor_precision=True,
        deduplicate=True,
    )

    if not xml_output:
        return {
            "article_text": "",
            "author": "",
            "language": "",
        }

    return parse_trafilatura_xml(xml_output)


def fetch_article_data(url: str) -> Dict[str, Any]:
    """
    Fetch an article page and extract the article text plus optional metadata.

    Success rules:
    - HTML download must succeed
    - extracted article_text must exist
    - word_count must be at least MIN_SUCCESS_WORD_COUNT

    Optional metadata:
    - author
    - language
    """
    try:
        html = download_article_html(url)
        html_fetched_at = utc_now_iso()

        extracted = extract_article_data_from_html(html, url)

        article_text = normalize_whitespace(extracted["article_text"])
        word_count = count_words(article_text)
        author = safe_strip(extracted["author"])
        language = safe_strip(extracted["language"])

        if word_count < MIN_SUCCESS_WORD_COUNT:
            return {
                "article_text": "",
                "word_count": 0,
                "author": author,
                "language": language,
                "article_fetch_success": False,
                "article_fetch_error": (
                    f"Extracted article text was too short "
                    f"({word_count} words, minimum is {MIN_SUCCESS_WORD_COUNT})."
                ),
                "html_fetched_at": html_fetched_at,
            }

        return {
            "article_text": article_text,
            "word_count": word_count,
            "author": author,
            "language": language,
            "article_fetch_success": True,
            "article_fetch_error": None,
            "html_fetched_at": html_fetched_at,
        }

    except requests.RequestException as error:
        return {
            "article_text": "",
            "word_count": 0,
            "author": "",
            "language": "",
            "article_fetch_success": False,
            "article_fetch_error": f"HTTP error: {str(error)}",
            "html_fetched_at": None,
        }
    except Exception as error:
        return {
            "article_text": "",
            "word_count": 0,
            "author": "",
            "language": "",
            "article_fetch_success": False,
            "article_fetch_error": f"Unexpected error: {str(error)}",
            "html_fetched_at": None,
        }


# -----------------------------
# Feed parsing
# -----------------------------

def get_entry_description(entry: Any) -> str:
    """Get the raw description/summary from an RSS entry."""
    if hasattr(entry, "summary") and entry.summary:
        return entry.summary
    if hasattr(entry, "description") and entry.description:
        return entry.description
    return ""


def build_item_from_entry(source_name: str, entry: Any) -> Optional[Dict[str, Any]]:
    """
    Build one stored item from one RSS entry.

    Save the item as long as the entry has a usable link.
    Article extraction success/failure is tracked separately.
    """
    link = safe_strip(getattr(entry, "link", ""))

    if not link:
        return None

    title = safe_strip(getattr(entry, "title", ""))
    published = safe_strip(getattr(entry, "published", ""))
    raw_description = get_entry_description(entry)
    description = remove_html_tags(raw_description)

    article_data = fetch_article_data(link)

    item = {
        "source": source_name,
        "title": title,
        "author": article_data["author"],
        "link": link,
        "published": published,
        "language": article_data["language"],
        "description": description,
        "article_text": article_data["article_text"],
        "word_count": article_data["word_count"],
        "article_fetch_success": article_data["article_fetch_success"],
        "article_fetch_error": article_data["article_fetch_error"],
        "html_fetched_at": article_data["html_fetched_at"],
        "collected_at": utc_now_iso(),
    }

    return item


def fetch_new_items(existing_links: Set[str]) -> List[Dict[str, Any]]:
    """Fetch all configured feeds and return only new items."""
    new_items: List[Dict[str, Any]] = []

    for feed_config in RSS_FEEDS:
        source_name = feed_config["source"]
        feed_url = feed_config["url"]

        print(f"\n===== {source_name} =====")
        parsed_feed = feedparser.parse(feed_url)

        if getattr(parsed_feed, "bozo", False):
            print(f"Warning: feed parsing issue for {source_name}")

        entries = parsed_feed.entries[:MAX_ITEMS_PER_FEED]

        for entry in entries:
            link = safe_strip(getattr(entry, "link", ""))

            if not link:
                continue

            if link in existing_links:
                continue

            title = safe_strip(getattr(entry, "title", "(no title)"))
            print(f"- {title}")

            item = build_item_from_entry(source_name, entry)
            if item is None:
                continue

            new_items.append(item)
            existing_links.add(link)

    return new_items


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    ensure_data_dir()

    existing_items = load_existing_items()
    existing_links = build_existing_link_set(existing_items)

    new_items = fetch_new_items(existing_links)
    all_items = existing_items + new_items

    save_items(all_items)

    print(f"\nAdded {len(new_items)} new items")
    print(f"Total stored items: {len(all_items)}")
    print(f"Saved RSS items to {OUTPUT_FILE}")

    if new_items:
        success_count = sum(1 for item in new_items if item["article_fetch_success"])
        failed_count = len(new_items) - success_count

        print(f"Successful article fetches: {success_count}")
        print(f"Failed article fetches: {failed_count}")


if __name__ == "__main__":
    main()