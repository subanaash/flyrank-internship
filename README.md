# Polite Scraper — Books to Scrape

## Target classification

**Site:** https://books.toscrape.com

**Why this site:** Books to Scrape is a sandbox built specifically for practicing web scraping. The site states this directly on its own homepage — it exists so people can learn scraping without touching a real business's infrastructure.

**Scope:** Only the first 3 catalogue pages (`/catalogue/page-1.html` through `page-3.html`), which link to 60 total book detail pages. No other pages or sections of the site are touched.

**Data collected:** For each book — title, product URL, price, availability, star rating, description, and provenance (source page + fetch timestamp). No personal data, no account data, no content outside the public book catalogue.

**robots.txt result:** Requested `https://books.toscrape.com/robots.txt` — returned 404 Not Found. No robots.txt file exists on this site. A missing file is not the same as explicit permission, but combined with the site's own stated purpose as a scraping sandbox, this confirms it's appropriate to scrape here.

**Why this is appropriate:** The site is explicitly built for this exact use case, the data collected is public catalogue information with no personal or sensitive content, and the assignment scope (3 pages, 60 books) is small and deliberate rather than a full-site crawl.

I will not reuse this code on another site without checking its rules and terms first.
