import json
from pathlib import Path
from datetime import datetime, timezone


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Input and output data files
INPUT_FILE = BASE_DIR / "data" / "rss_items.json"
OUTPUT_FILE = BASE_DIR / "data" / "enriched_items.json"


def load_items(file_path: Path) -> list:
    """Load items from a JSON file."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return []

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_items(file_path: Path, items: list) -> None:
    """Save items to a JSON file."""
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(items, file, indent=2, ensure_ascii=False)


def normalize_text(text: str) -> str:
    """Clean whitespace and line breaks."""
    if not text:
        return ""
    return " ".join(text.split())


def create_summary(text: str, max_length: int = 240) -> str:
    """
    Create a simple summary for MVP.
    This trims the cleaned text to a maximum length.
    """
    clean_text = normalize_text(text)

    if len(clean_text) <= max_length:
        return clean_text

    return clean_text[:max_length].rstrip() + "..."


def enrich_item(item: dict) -> dict:
    """Add enrichment fields to an item."""
    enriched_item = item.copy()

    source_text = enriched_item.get("clean_description", "")
    clean_text = normalize_text(source_text)

    enriched_item["summary"] = create_summary(clean_text)
    enriched_item["text_length"] = len(clean_text)
    enriched_item["enriched_at"] = datetime.now(timezone.utc).isoformat()

    return enriched_item


def main():
    items = load_items(INPUT_FILE)

    if not items:
        print("No items found to enrich.")
        return

    enriched_items = [enrich_item(item) for item in items]

    save_items(OUTPUT_FILE, enriched_items)

    print(f"Loaded {len(items)} items from {INPUT_FILE}")
    print(f"Saved {len(enriched_items)} enriched items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()