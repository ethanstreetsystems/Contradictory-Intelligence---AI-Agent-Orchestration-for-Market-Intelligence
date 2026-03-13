# Contradictory Intelligence (CI) — Project Brief

## What this project does
Ingests industry newsletters via RSS, fetches full article text, and extracts structured market intelligence: summaries, topics, tags, strategic implications, and investment signals (tickers, sectors, winners/losers).

## Pipeline (3 stages, run in order)

| Stage | Script | Input | Output |
|-------|--------|-------|--------|
| 1 | `src/rss_ingest.py` | RSS feeds (hardcoded) | `data/rss_items.json` |
| 2 | `src/pass1enrich_items.py` | `rss_items.json` | `data/pass1enriched_items.json` |
| 3 | `src/pass2enrich_items.py` | `pass1enriched_items.json` | `data/pass2enriched_items.json` |

**Stage 1** — Fetches feeds (Import AI, Peter Diamandis), downloads full article HTML via `requests`, extracts clean text with `trafilatura`. Deduplicates by URL. Tracks `article_fetch_success`.

**Stage 2** — Cleans text, normalizes dates, assigns stable SHA-256 IDs, sets `enrichment_status` (`ready_for_ai` or `skipped`), and creates empty placeholder fields for AI output.

**Stage 3** — Sends each `ready_for_ai` article to Claude (`claude-sonnet-4-6` by default, overridable via `CI_PASS2_MODEL` env var). Uses Anthropic SDK with tool use for structured JSON output. Has resume logic: already-completed records are skipped. Safety limits via env vars: `CI_MAX_ITEMS_PER_RUN` (30), `CI_MAX_TOTAL_INPUT_CHARS_PER_RUN` (300000), `CI_MAX_TEXT_CHARS` (12000).

## AI output fields (pass 2)
- `ai_summary_short` — 2-3 sentence summary
- `ai_summary_bullets` — 3-5 key point bullets
- `primary_topic`, `secondary_topics`, `tags`
- `strategic_implications` — what matters and why
- `investment_implications` — `potential_winners`, `potential_losers`, `mentioned_tickers`, `implied_tickers`, `implied_sectors`, `signal_strength` (0–10 int)

## Status fields
- `enrichment_status`: `ready_for_ai` | `skipped`
- `pass2_status`: `completed` | `failed` | `skipped` | `deferred` | `processing`

## Stack
Python, `feedparser`, `trafilatura`, `requests`, `anthropic` SDK, JSON files. No database.

## Key file paths
```
src/rss_ingest.py          # Stage 1
src/pass1enrich_items.py   # Stage 2
src/pass2enrich_items.py   # Stage 3
src/main.py                # Placeholder (not wired up yet)
data/rss_items.json        # Raw fetched articles
data/pass1enriched_items.json
data/pass2enriched_items.json
data/analyzed_items.json   # (exists but not yet used in pipeline)
docs/PHASE_1_ARCHITECTURE.md
docs/PHASE_2_IMPLEMENTATION.md
```

## Goals / status
MVP is functional end-to-end. Next steps likely involve: wiring `main.py` as an orchestrator, or building a frontend or export layer.

## Note
User is relatively new to coding — explain things clearly and avoid jargon.
