# Phase 1: Product Architecture and Initial Data Sources

## 1. Golden Path MVP
Ingest → Normalize → Store → Display

Goal: prove the system can automatically collect market information and show it in one place.

Define what Phase 1 includes and excludes.

---

## 2. Initial Data Sources
## Initial Data Sources

The initial sources for Phase 1 are selected based on two criteria:
1. They are part of the founder’s real research workflow
2. They can be accessed via RSS or structured web feeds

These sources focus on emerging technology, venture capital, and future-oriented investment themes.

Source: Metatrends (Peter Diamandis)
Type: Newsletter
Access Method: RSS
URL: https://metatrends.substack.com/feed
Reason: Future technology and exponential tech trends relevant to investment research.

Source: ARK Invest Research
Type: Research / Blog
Access Method: RSS
Feed URL: https://ark-invest.com/feed/
Reason: Research and commentary on disruptive innovation including AI, robotics, genomics, crypto, and energy.

Source: a16z Newsletter
Type: Newsletter / Blog
Access Method: RSS
Feed URL: https://www.a16z.news/feed
Reason: Commentary and analysis on startups, AI, software, and emerging technology.


---

## 3. Standard Data Format
Define the standard object every item becomes.

All sources will be converted into one standard format so they can be stored and displayed consistently.

Draft fields:

- id
- source_name
- title
- author
- published_date
- url
- raw_text
- summary (optional)
- tags (optional)

This format may change after reviewing the actual data from the selected sources.

---

## 4. Architecture + Stack

Define the core technology choices used in the Phase 1 MVP.

The system architecture follows a simple pipeline:

Ingest → Normalize → Analyze → Store → Display


### Backend

Language: Python

Responsibilities:

- Fetch RSS feeds
- Extract article content
- Convert items into the standard format
- Run AI analysis
- Save items to the database

Python is used because it has strong libraries for RSS feeds, data pipelines, and AI workflows.


### Database

Database: PostgreSQL

Stores structured data for each item:

- id
- source_name
- title
- author
- published_date
- url
- raw_text
- summary
- analysis
- investment_implications
- tags (optional)


### Frontend

Simple web interface that displays collected items.

Phase 1 UI should show:

- title
- source
- publish date
- summary
- analysis
- investment implications
- link to original article

Goal: prove the system can turn raw source content into useful investor-facing output.


### Job Scheduler

The system runs on a schedule and checks the selected feeds for new content.

Initial schedule:

- every other day

Reason:

- keeps the MVP simple
- reduces unnecessary AI processing
- helps control API costs during early development


### System Flow

RSS Feed  
↓  
Python ingestion script  
↓  
Normalize to standard format  
↓  
Run AI analysis  
↓  
Store in database  
↓  
Frontend displays items

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
