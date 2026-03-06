# Phase 1: Product Architecture and Initial Data Sources

## 1. Golden Path MVP
Ingest → Normalize → Store → Display

Goal: prove the system can automatically collect market information and show it in one place.

Define what Phase 1 includes and excludes.

---

## 2. Initial Data Sources
Select 3–5 high-signal sources that are easy to ingest (RSS/API preferred).

For each source document:
- Source name
- URL
- Access method (RSS/API/web)
- Update frequency
- Why it matters

---

## 3. Canonical Data Model
Define the standard object every item becomes.

Example fields:
- id
- title
- source
- url
- published_date
- raw_text
- summary (optional later)
- tags (optional later)

---

## 4. Architecture + Stack
Define the core technology choices.

Example:
- Backend
- Database
- Frontend
- Job scheduler

Define how the system components interact.

---

## 5. Ingestion + Normalization
For each source define:
- how data is fetched
- how content is parsed
- deduplication logic
- error handling
- how ingestion state is tracked

---

## 6. Storage + Retrieval
Define:
- database structure
- how items are stored
- how the feed is queried
- indexes or keys for speed and deduplication

---

## 7. Minimal UI Screens
Define the basic interface.

Example:
- feed page (latest items)
- item detail page
- filters or search (optional)

---

## 8. Minimal AI Enrichment (Optional)
Decide whether Phase 1 includes:
- summaries
- tags
- ticker extraction

If included, define exactly what gets generated.

---

## 9. Deployment + Environment
Define:
- where the system runs
- how jobs are scheduled
- API key / secret management

---

## 10. Phase 1 Success Criteria
Define what “done” means.

Examples:
- items ingest automatically
- no duplicate records
- feed displays correctly
- links work
- data matches original sources
