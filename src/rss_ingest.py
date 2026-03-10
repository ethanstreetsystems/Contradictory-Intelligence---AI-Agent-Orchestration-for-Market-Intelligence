import urllib.request
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone


RSS_FEEDS = {
    "MetaTrends": "https://metatrends.substack.com/feed",
    "ARK Invest": "https://ark-invest.com/feed/",
    "a16z": "https://www.a16z.news/feed",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "../data/rss_items.json")


def load_existing_items():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def fetch_rss_items(source_name, url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    response = urllib.request.urlopen(request)
    data = response.read()

    root = ET.fromstring(data)

    channel = root.find("channel")
    if channel is None:
        print(f"\nNo channel found for {source_name}")
        return []

    items = channel.findall("item")

    print(f"\n===== {source_name} =====\n")

    feed_items = []

    for item in items[:5]:
        title = item.find("title")
        link = item.find("link")
        pub_date = item.find("pubDate")
        description = item.find("description")

        if title is not None and title.text is not None:
            print("-", title.text)

            article = {
                "source": source_name,
                "title": title.text,
                "link": link.text if link is not None else None,
                "published": pub_date.text if pub_date is not None else None,
                "description": description.text if description is not None and description.text is not None else None,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }

            feed_items.append(article)

    return feed_items


def merge_new_items(existing_items, new_items):
    existing_links = set()

    for item in existing_items:
        if item.get("link"):
            existing_links.add(item["link"])

    added_count = 0

    for item in new_items:
        link = item.get("link")

        if link and link not in existing_links:
            existing_items.append(item)
            existing_links.add(link)
            added_count += 1

    return existing_items, added_count


if __name__ == "__main__":
    existing_items = load_existing_items()
    new_items = []

    for source_name, url in RSS_FEEDS.items():
        items = fetch_rss_items(source_name, url)
        new_items.extend(items)

    updated_items, added_count = merge_new_items(existing_items, new_items)

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(updated_items, file, indent=2)

    print(f"\nAdded {added_count} new items.")
    print(f"Total stored items: {len(updated_items)}")
    print("Saved RSS items to data/rss_items.json")