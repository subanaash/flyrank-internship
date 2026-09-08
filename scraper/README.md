# Polite Scraper — Books to Scrape

A small, polite scraping pipeline that downloads the first 3 catalogue pages of [Books to Scrape](https://books.toscrape.com), visits all 60 book detail pages, turns messy HTML into clean, schema-validated JSON, survives a broken page without crashing, and ends every run with an honest report.

## Target classification

**Site:** https://books.toscrape.com

**Why this site:** Books to Scrape is a sandbox built specifically for practicing web scraping. The site states this directly on its own homepage — it exists so people can learn scraping without touching a real business's infrastructure.

**Scope:** Only the first 3 catalogue pages (`/catalogue/page-1.html` through `page-3.html`), which link to 60 total book detail pages. No other pages or sections of the site are touched.

**Data collected:** For each book — title, product URL, price, availability, star rating, description, and provenance (source page + fetch timestamp). No personal data, no account data, no content outside the public book catalogue.

**robots.txt result:** Requested `https://books.toscrape.com/robots.txt` — returned 404 Not Found. No robots.txt file exists on this site. A missing file is not the same as explicit permission, but combined with the site's own stated purpose as a scraping sandbox, this confirms it's appropriate to scrape here.

I will not reuse this code on another site without checking its rules and terms first.

## How to run it

1. Clone the repo and enter the scraper folder:
   ```
   git clone https://github.com/subanaash/flyrank-internship.git
   cd flyrank-internship/scraper
   ```

2. Create a virtual environment and activate it:
   ```
   python3 -m venv venv
   venv\Scripts\activate   # on Mac/Linux: source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install requests beautifulsoup4 pydantic
   ```

4. Run the scraper:
   ```
   python src/main.py
   ```

First run fetches all 63 pages live (takes roughly 30–40 seconds due to the polite delay). Subsequent runs read from `cache/` and finish in a few seconds. Output lands in `output/books.json`, `output/errors.json`, and `output/run-report.json`.

## Record schema

Each validated record in `books.json` has this shape:

| Field | Type | Notes |
|---|---|---|
| `title` | string | required |
| `product_url` | string | required, canonical identity, must start with `https://` |
| `price_gbp` | float | required, parsed from `price_text` |
| `price_text` | string | required, original raw value (e.g. `£51.77`) kept alongside the clean one |
| `availability_text` | string | required |
| `rating` | int or null | 1–5, parsed from the word rating on the page |
| `description` | string or null | null when the page has no description — never invented |
| `source_page` | string | required, which catalogue page this book was discovered on |
| `fetched_at` | string | required, ISO 8601 UTC timestamp |

Records that fail validation are written to `errors.json` with a reason instead of being silently dropped or force-included.

## Politeness rules

- **User-agent:** every request identifies itself as `FlyRankInternshipA9/1.0 (+https://github.com/subanaash/flyrank-internship)`.
- **Timeout:** every request gives up after 10 seconds rather than hanging indefinitely.
- **Delay:** at least 500ms between real requests to the site. Cached pages are read locally and never trigger a delay or a new request.
- **Cache:** every page is saved to `cache/` on first fetch. All development and re-runs read from cache instead of re-hitting the site.
- **Retry logic:** timeouts and 5xx server errors get one retry after a short wait. 404s and 403s are never retried — the site has already given a definitive answer.
- **Status check:** only a 200 response is treated as real HTML to parse. Anything else is logged as a failed fetch.

## Proof of a run — run-report.json

```json
{
  "start_time": "2026-08-25T12:04:25Z",
  "duration_seconds": 3.18,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0
}
```

This run read entirely from cache (63 cache hits, 0 new fetches), produced exactly 60 valid records, and had zero failures — proving the pipeline is idempotent: re-running it doesn't duplicate or lose data.

A separate test run with one deliberately broken URL added to the list confirmed failure handling works correctly: the run still finished, `books.json` still held the 60 good records, and `run-report.json` showed `failed_pages: 1` — the fake page was skipped and logged, not allowed to crash the run.

## Why this assignment needed no browser

The data needed for every field (title, price, availability, rating, description) is already present in the raw HTML the server sends back on first request — there's no JavaScript rendering step that fetches this content afterward. A headless browser like Playwright would add real cost (memory, startup time, complexity) for zero benefit here, since a plain HTTP request already returns everything needed.

## Ethics note

I only scraped a site explicitly built and labeled as a scraping practice sandbox, and only the specific pages this assignment required — not the whole site. Where an official API exists for a real product or service, that should always be used instead of scraping. This scraper never attempts to bypass logins, paywalls, or explicit blocks, and it only collects the minimum data needed for the task, nothing more.

## Known limitation

Descriptions on some book pages contain a duplicated excerpt (the site itself repeats a snippet before the full description in its HTML) — this is preserved as-is from the source rather than cleaned further, since the assignment's normalization step focuses on price and rating, not de-duplicating the site's own content.
