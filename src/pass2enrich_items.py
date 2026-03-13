import json
import os
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import anthropic
from dotenv import load_dotenv
load_dotenv()


# ============================================================
# CONFIG
# ============================================================
# Base project folder:
# If this file is in /src, parent.parent should be the project root.
BASE_DIR = Path(__file__).resolve().parent.parent

# Input and output files
INPUT_PATH = BASE_DIR / "data" / "pass1enriched_items.json"
OUTPUT_PATH = BASE_DIR / "data" / "pass2enriched_items.json"

# Model settings
MODEL_NAME = os.getenv("CI_PASS2_MODEL", "claude-sonnet-4-6")

# Cost / usage safety settings
MAX_TEXT_CHARS = int(os.getenv("CI_MAX_TEXT_CHARS", "12000"))
MAX_ITEMS_PER_RUN = int(os.getenv("CI_MAX_ITEMS_PER_RUN", "30"))
MAX_TOTAL_INPUT_CHARS_PER_RUN = int(os.getenv("CI_MAX_TOTAL_INPUT_CHARS_PER_RUN", "300000"))

# Small pause between API requests
REQUEST_DELAY_SECONDS = float(os.getenv("CI_REQUEST_DELAY_SECONDS", "0.5"))

# Create the API client
client = anthropic.Anthropic()


# ============================================================
# BASIC HELPERS
# ============================================================
def utc_now_iso() -> str:
    """Return current UTC time as an ISO string."""
    return datetime.now(timezone.utc).isoformat()


def load_json_file(path: Path) -> Any:
    """Read JSON from a file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(path: Path, data: Any) -> None:
    """Write JSON to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_string(value: Any) -> str:
    """Make sure a value is a clean string."""
    if isinstance(value, str):
        return value.strip()
    return ""


def ensure_list_of_strings(value: Any) -> List[str]:
    """Make sure a value is a list of non-empty strings."""
    if not isinstance(value, list):
        return []

    cleaned = []
    for item in value:
        if isinstance(item, str):
            item = item.strip()
            if item:
                cleaned.append(item)
    return cleaned


def clamp_signal_strength(value: Any) -> int:
    """Force signal strength to stay between 0 and 10."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(10, value))


def truncate_text(text: str, max_chars: int) -> str:
    """Cut text down if it is too long."""
    text = ensure_string(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def build_record_lookup(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Build a lookup table by article id.
    Example:
    {
        "article_123": {...record...},
        "article_456": {...record...}
    }
    """
    lookup = {}
    for record in records:
        record_id = record.get("id")
        if record_id:
            lookup[record_id] = record
    return lookup


# ============================================================
# OUTPUT SCHEMA FOR THE MODEL
# ============================================================
def build_schema() -> Dict[str, Any]:
    """
    This tells the model exactly what JSON shape we want back.
    The descriptions matter. They help the model understand each field.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ai_summary_short": {
                "type": "string",
                "description": "A concise 2-3 sentence summary of the article."
            },
            "ai_summary_bullets": {
                "type": "array",
                "description": "3-5 concise bullets that capture the key points of the article.",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 5
            },
            "primary_topic": {
                "type": "string",
                "description": "The main topic of the article."
            },
            "secondary_topics": {
                "type": "array",
                "description": "Supporting or adjacent topics discussed in the article.",
                "items": {"type": "string"},
                "maxItems": 5
            },
            "tags": {
                "type": "array",
                "description": "Short labels useful for grouping, filtering, or later analysis.",
                "items": {"type": "string"},
                "maxItems": 8
            },
            "strategic_implications": {
                "type": "array",
                "description": "Concrete strategic implications, what matters, and why it matters.",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 5
            },
            "investment_implications": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "potential_winners": {
                        "type": "array",
                        "description": "Companies, protocols, crypto assets, ecosystems, or categories that may benefit.",
                        "items": {"type": "string"},
                        "maxItems": 8
                    },
                    "potential_losers": {
                        "type": "array",
                        "description": "Companies, protocols, crypto assets, ecosystems, or categories that may be hurt.",
                        "items": {"type": "string"},
                        "maxItems": 8
                    },
                    "mentioned_tickers": {
                        "type": "array",
                        "description": "Only symbols explicitly written in the article text, including stock tickers, ETFs, crypto assets, or blockchain project tokens.",
                        "items": {"type": "string"},
                        "maxItems": 12
                    },
                    "implied_tickers": {
                        "type": "array",
                        "description": "Reasonable inferred market symbols based on the article, including stocks, ETFs, crypto assets, or blockchain project tokens, even if not explicitly written.",
                        "items": {"type": "string"},
                        "maxItems": 12
                    },
                    "implied_sectors": {
                        "type": "array",
                        "description": "Industries, market segments, investment themes, or crypto ecosystems affected or discussed by the article.",
                        "items": {"type": "string"},
                        "maxItems": 8
                    },
                    "signal_strength": {
                        "type": "integer",
                        "description": "0 to 10 rating for how strong and actionable the investment signal appears to be.",
                        "minimum": 0,
                        "maximum": 10
                    }
                },
                "required": [
                    "potential_winners",
                    "potential_losers",
                    "mentioned_tickers",
                    "implied_tickers",
                    "implied_sectors",
                    "signal_strength"
                ]
            }
        },
        "required": [
            "ai_summary_short",
            "ai_summary_bullets",
            "primary_topic",
            "secondary_topics",
            "tags",
            "strategic_implications",
            "investment_implications"
        ]
    }


# ============================================================
# PROMPT
# ============================================================
def build_prompt(record: Dict[str, Any]) -> str:
    """
    Build the prompt sent to the model.
    We pass in article metadata plus cleaned article text.
    """
    title = ensure_string(record.get("title"))
    source = ensure_string(record.get("source"))
    link = ensure_string(record.get("link"))
    published_at = ensure_string(record.get("published_at"))
    cleaned_text = truncate_text(record.get("cleaned_text", ""), MAX_TEXT_CHARS)

    return f"""
You are enriching one article for a market intelligence system called Contradictory Intelligence.

Your job is to read the article text and return structured intelligence in valid JSON only.

Rules:
- Be concrete, not vague.
- Stay grounded in the article.
- Do not invent facts that are not supported by the text.
- You may infer implications when reasonable, but do not overreach.
- If investment implications are weak, keep the lists short and use a lower signal_strength.
- "mentioned_tickers" means only symbols explicitly written in the article text.
- "implied_tickers" can include reasonable inferred market symbols such as stocks, ETFs, crypto assets, or blockchain project tokens.
- "implied_sectors" can include industries, investment themes, market segments, or crypto ecosystems.
- "ai_summary_short" must be 2-3 sentences.
- "ai_summary_bullets" must contain 3-5 bullets.
- "strategic_implications" should explain what matters strategically, not just restate the article.
- "signal_strength" must be an integer from 0 to 10.

Article metadata:
Title: {title}
Source: {source}
Published At: {published_at}
Link: {link}

Article text:
\"\"\"
{cleaned_text}
\"\"\"
""".strip()


# ============================================================
# MODEL CALL
# ============================================================
def call_model(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send the article to the model and get structured JSON back.
    """
    schema = build_schema()
    prompt = build_prompt(record)

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=4096,
        temperature=0.2,
        tools=[
            {
                "name": "ci_pass2_enrichment",
                "description": "Return structured market intelligence extracted from the article.",
                "input_schema": schema,
            }
        ],
        tool_choice={"type": "tool", "name": "ci_pass2_enrichment"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    raise ValueError("Model did not return a tool_use block.")


# ============================================================
# CLEAN / NORMALIZE MODEL OUTPUT
# ============================================================
def normalize_ai_output(ai_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Even though the model should follow the schema, we still clean the output
    so our saved JSON stays predictable.
    """
    investment = ai_data.get("investment_implications", {})

    return {
        "ai_summary_short": ensure_string(ai_data.get("ai_summary_short")),
        "ai_summary_bullets": ensure_list_of_strings(ai_data.get("ai_summary_bullets")),
        "primary_topic": ensure_string(ai_data.get("primary_topic")),
        "secondary_topics": ensure_list_of_strings(ai_data.get("secondary_topics")),
        "tags": ensure_list_of_strings(ai_data.get("tags")),
        "strategic_implications": ensure_list_of_strings(ai_data.get("strategic_implications")),
        "investment_implications": {
            "potential_winners": ensure_list_of_strings(investment.get("potential_winners")),
            "potential_losers": ensure_list_of_strings(investment.get("potential_losers")),
            "mentioned_tickers": ensure_list_of_strings(investment.get("mentioned_tickers")),
            "implied_tickers": ensure_list_of_strings(investment.get("implied_tickers")),
            "implied_sectors": ensure_list_of_strings(investment.get("implied_sectors")),
            "signal_strength": clamp_signal_strength(investment.get("signal_strength")),
        }
    }


# ============================================================
# SINGLE RECORD ENRICHMENT
# ============================================================
def enrich_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process one article through Pass 2.
    """
    updated = deepcopy(record)

    updated["pass2_status"] = "processing"
    updated["pass2_error"] = None
    updated["pass2_enriched_at"] = None

    cleaned_text = ensure_string(updated.get("cleaned_text"))
    if not cleaned_text:
        updated["pass2_status"] = "skipped"
        updated["pass2_error"] = "Missing cleaned_text."
        return updated

    try:
        ai_raw = call_model(updated)
        ai_clean = normalize_ai_output(ai_raw)

        updated["ai_summary_short"] = ai_clean["ai_summary_short"]
        updated["ai_summary_bullets"] = ai_clean["ai_summary_bullets"]
        updated["primary_topic"] = ai_clean["primary_topic"]
        updated["secondary_topics"] = ai_clean["secondary_topics"]
        updated["tags"] = ai_clean["tags"]
        updated["strategic_implications"] = ai_clean["strategic_implications"]
        updated["investment_implications"] = ai_clean["investment_implications"]

        updated["pass2_status"] = "completed"
        updated["pass2_error"] = None
        updated["pass2_enriched_at"] = utc_now_iso()

    except Exception as e:
        updated["pass2_status"] = "failed"
        updated["pass2_error"] = str(e)
        updated["pass2_enriched_at"] = utc_now_iso()

    return updated


# ============================================================
# MAIN
# ============================================================
def main() -> None:
    # --------------------------------------------------------
    # Step 1: Load Pass 1 input
    # --------------------------------------------------------
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    pass1_records = load_json_file(INPUT_PATH)

    if not isinstance(pass1_records, list):
        raise ValueError("Expected pass1enriched_items.json to contain a list of records.")

    print(f"Loaded {len(pass1_records)} records from:")
    print(INPUT_PATH)

    # --------------------------------------------------------
    # Step 2: Load existing Pass 2 output if it exists
    # This is what gives us resume logic.
    # --------------------------------------------------------
    existing_pass2_records: List[Dict[str, Any]] = []
    existing_lookup: Dict[str, Dict[str, Any]] = {}

    if OUTPUT_PATH.exists():
        existing_pass2_records = load_json_file(OUTPUT_PATH)
        if isinstance(existing_pass2_records, list):
            existing_lookup = build_record_lookup(existing_pass2_records)
            print(f"Found existing Pass 2 output with {len(existing_pass2_records)} records.")
            print("Resume logic is ON: completed records will be skipped.")
        else:
            print("Warning: existing Pass 2 file is not a valid list. Ignoring it.")

    # --------------------------------------------------------
    # Step 3: Build the new output list
    # We start from Pass 1 records and merge in prior Pass 2 work when useful.
    # --------------------------------------------------------
    output_records: List[Dict[str, Any]] = []

    processed_this_run = 0
    skipped_completed = 0
    skipped_not_ready = 0
    failed_this_run = 0
    completed_this_run = 0
    total_input_chars_this_run = 0

    for index, pass1_record in enumerate(pass1_records, start=1):
        record_id = pass1_record.get("id")
        enrichment_status = pass1_record.get("enrichment_status")

        # Use a fresh copy of the Pass 1 record as the base.
        current_record = deepcopy(pass1_record)

        # If we already have a Pass 2 version of this record, grab it.
        existing_pass2_record = existing_lookup.get(record_id)

        # ----------------------------------------------------
        # Skip records that are not ready for AI
        # ----------------------------------------------------
        if enrichment_status != "ready_for_ai":
            if existing_pass2_record:
                output_records.append(existing_pass2_record)
            else:
                current_record["pass2_status"] = "skipped"
                current_record["pass2_error"] = f"Pass 1 status is '{enrichment_status}', not 'ready_for_ai'."
                current_record["pass2_enriched_at"] = None
                output_records.append(current_record)

            skipped_not_ready += 1
            print(f"[{index}/{len(pass1_records)}] Skipped (not ready_for_ai): {current_record.get('title', 'Untitled')}")
            continue

        # ----------------------------------------------------
        # Resume logic:
        # If already completed in a previous run, skip it.
        # ----------------------------------------------------
        if existing_pass2_record and existing_pass2_record.get("pass2_status") == "completed":
            output_records.append(existing_pass2_record)
            skipped_completed += 1
            print(f"[{index}/{len(pass1_records)}] Skipped (already completed): {current_record.get('title', 'Untitled')}")
            continue

        # ----------------------------------------------------
        # Safety limit: max number of new items this run
        # ----------------------------------------------------
        if processed_this_run >= MAX_ITEMS_PER_RUN:
            if existing_pass2_record:
                output_records.append(existing_pass2_record)
            else:
                current_record["pass2_status"] = "deferred"
                current_record["pass2_error"] = f"Deferred because MAX_ITEMS_PER_RUN ({MAX_ITEMS_PER_RUN}) was reached."
                current_record["pass2_enriched_at"] = None
                output_records.append(current_record)

            print(f"[{index}/{len(pass1_records)}] Deferred (run item limit reached): {current_record.get('title', 'Untitled')}")
            continue

        # ----------------------------------------------------
        # Safety limit: total input chars this run
        # ----------------------------------------------------
        cleaned_text = truncate_text(pass1_record.get("cleaned_text", ""), MAX_TEXT_CHARS)
        article_chars = len(cleaned_text)

        if total_input_chars_this_run + article_chars > MAX_TOTAL_INPUT_CHARS_PER_RUN:
            if existing_pass2_record:
                output_records.append(existing_pass2_record)
            else:
                current_record["pass2_status"] = "deferred"
                current_record["pass2_error"] = (
                    f"Deferred because MAX_TOTAL_INPUT_CHARS_PER_RUN "
                    f"({MAX_TOTAL_INPUT_CHARS_PER_RUN}) would be exceeded."
                )
                current_record["pass2_enriched_at"] = None
                output_records.append(current_record)

            print(f"[{index}/{len(pass1_records)}] Deferred (char limit reached): {current_record.get('title', 'Untitled')}")
            continue

        # ----------------------------------------------------
        # Process this record with the model
        # ----------------------------------------------------
        print(f"[{index}/{len(pass1_records)}] Processing: {current_record.get('title', 'Untitled')}")

        updated_record = enrich_record(current_record)
        output_records.append(updated_record)

        processed_this_run += 1
        total_input_chars_this_run += article_chars

        if updated_record.get("pass2_status") == "completed":
            completed_this_run += 1
            print("  -> Pass 2 completed")
        else:
            failed_this_run += 1
            print(f"  -> Pass 2 failed: {updated_record.get('pass2_error')}")

        time.sleep(REQUEST_DELAY_SECONDS)

    # --------------------------------------------------------
    # Step 4: Save output
    # --------------------------------------------------------
    save_json_file(OUTPUT_PATH, output_records)

    # --------------------------------------------------------
    # Step 5: Print summary
    # --------------------------------------------------------
    print("\nDone.")
    print(f"Total Pass 1 records:                 {len(pass1_records)}")
    print(f"Already completed and skipped:        {skipped_completed}")
    print(f"Not ready_for_ai and skipped:         {skipped_not_ready}")
    print(f"New records processed this run:       {processed_this_run}")
    print(f"New records completed this run:       {completed_this_run}")
    print(f"New records failed this run:          {failed_this_run}")
    print(f"Total input chars used this run:      {total_input_chars_this_run}")
    print(f"MAX_ITEMS_PER_RUN:                    {MAX_ITEMS_PER_RUN}")
    print(f"MAX_TOTAL_INPUT_CHARS_PER_RUN:        {MAX_TOTAL_INPUT_CHARS_PER_RUN}")
    print(f"Saved Pass 2 output to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()