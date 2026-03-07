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
- summary
- analysis
- investment_implications
- tags (optional)
- created_at

This format may change after reviewing the actual data from the selected sources.

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

For each source, define:

- how data is fetched
- how content is parsed
- deduplication logic
- error handling
- how ingestion state is tracked


### Source 1: Metatrends (Peter Diamandis)

How data is fetched:

- The system checks the RSS feed URL
- New items are pulled from the feed

Content parsing:

- Extract title, author, publish date, article URL, description, and full article text from the RSS item
- Use the `content:encoded` field when available
- Remove HTML tags and clean the text before storing

Deduplication logic:

- Use the article URL as the main unique identifier
- If the URL already exists in the database, skip it

Error handling:

- If the feed cannot be reached, log the error and move on
- If a field is missing, store the item with the available fields and flag it for review

Ingestion state tracking:

- Track the last successful run time
- Track which article URLs have already been stored


### Source 2: ARK Invest

How data is fetched:

- The system checks the RSS feed URL
- New items are pulled from the feed

Content parsing:

- Extract title, publish date, article URL, description, and category from the RSS item
- If full article text is not included in the feed, open the article URL and extract the text from the page
- Clean the text before storing

Deduplication logic:

- Use the article URL as the main unique identifier
- If the URL already exists in the database, skip it

Error handling:

- If the feed cannot be reached, log the error and move on
- If the article page cannot be parsed, store the metadata only and flag it for review

Ingestion state tracking:

- Track the last successful run time
- Track which article URLs have already been stored


### Source 3: a16z

How data is fetched:

- The system checks the RSS feed URL
- New items are pulled from the feed

Content parsing:

- Extract title, author, publish date, article URL, description, and full article text from the RSS item
- Use the `content:encoded` field when available
- Remove HTML tags and clean the text before storing

Deduplication logic:

- Use the article URL as the main unique identifier
- If the URL already exists in the database, skip it

Error handling:

- If the feed cannot be reached, log the error and move on
- If a field is missing, store the item with the available fields and flag it for review

Ingestion state tracking:

- Track the last successful run time
- Track which article URLs have already been stored

---
## 6. Storage + Retrieval

Define:

- database structure
- how items are stored
- how the feed is queried
- indexes or keys for speed and deduplication


### Database Structure

Phase 1 uses one main table to store market intelligence items.

Each row represents one article or source item.

Main fields:

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
- tags
- created_at


### How Items Are Stored

After a source item is fetched and cleaned, it is converted into the standard data format.

The system then stores:

- source metadata
- article text
- AI-generated output
- timestamps

Each item is stored as a single record in the database.


### How the Feed Is Queried

The frontend will query the database for the most recent items.

Default feed behavior:

- sort by published_date, newest first
- show title, source, publish date, summary, analysis, and investment implications
- link back to the original article

Phase 1 retrieval should support:

- latest items feed
- filter by source
- simple search later if needed


### Indexes and Keys

Primary key:

- id

Unique key for deduplication:

- url

Indexes:

- published_date
- source_name

Reason:

- `url` prevents duplicate records
- `published_date` makes the main feed load faster
- `source_name` makes source filtering faster

---

## 7. Minimal UI Screens
Define the basic interface.

UI Version 1.0:
- feed page (latest items)
- item detail page
- filters or search (optional)

---

## 8. Minimal AI Enrichment

Define the AI-generated output added to each source item.

Version 1.0 of Contradictory Intelligence (CI) will generate the following fields:

- summary
- analysis
- investment_implications

Definitions:

- summary: a short overview of the article content
- analysis: key themes, ideas, or signals extracted from the article
- investment_implications: potential relevance for investing, including sectors, companies, or technologies that may benefit or be negatively impacted

Optional features for later versions:

- tags
- ticker extraction

Reason:

Version 1.0 should focus on transforming raw source content into structured intelligence that can help inform investment decisions while keeping the system simple.

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
