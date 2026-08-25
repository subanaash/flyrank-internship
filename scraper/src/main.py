import os
import re
import json
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
from typing import Optional
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError, field_validator

BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = "cache"
OUTPUT_DIR = "output"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/subanaash/flyrank-internship)"
TIMEOUT = 10
DELAY = 0.5

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# For the Stage 5 checkpoint: add one made-up URL to prove failure handling.
# Set to True to include it, False for a normal clean run.
INCLUDE_FAKE_URL_FOR_TESTING = False
FAKE_BOOK_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html"


# ---- Schema ----
class Book(BaseModel):
    title: str
    product_url: str
    price_gbp: float
    price_text: str
    availability_text: str
    rating: Optional[int] = None
    description: Optional[str] = None
    source_page: str
    fetched_at: str

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_https(cls, v):
        if not v.startswith("https://"):
            raise ValueError("URL must start with https://")
        return v


class FetchResult:
    def __init__(self, html: Optional[str], from_cache: bool, failed: bool, status_code: Optional[int] = None):
        self.html = html
        self.from_cache = from_cache
        self.failed = failed
        self.status_code = status_code


def fetch_page(url: str, cache_filename: str) -> FetchResult:
    """Fetch a page politely. Retries once on timeout/5xx. Never retries 404/403.
    Returns a FetchResult instead of raising, so one bad page can't kill the run."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_filename} ({len(html)} bytes)")
        return FetchResult(html=html, from_cache=True, failed=False, status_code=200)

    headers = {"User-Agent": USER_AGENT}
    attempts = 0
    max_attempts = 2

    while attempts < max_attempts:
        attempts += 1
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            print(f"FAILED (network error): {url} — {e}")
            if attempts < max_attempts:
                time.sleep(1)
                continue
            return FetchResult(html=None, from_cache=False, failed=True)

        if response.status_code == 200:
            response.encoding = "utf-8"
            html = response.text
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"FETCH: {cache_filename} ({len(html)} bytes, status 200)")
            time.sleep(DELAY)
            return FetchResult(html=html, from_cache=False, failed=False, status_code=200)

        if response.status_code in (404, 403):
            print(f"FAILED ({response.status_code}, not retrying): {url}")
            return FetchResult(html=None, from_cache=False, failed=True, status_code=response.status_code)

        if 500 <= response.status_code < 600:
            print(f"FAILED ({response.status_code}, will retry): {url}")
            if attempts < max_attempts:
                time.sleep(1)
                continue
            return FetchResult(html=None, from_cache=False, failed=True, status_code=response.status_code)

        print(f"FAILED (status {response.status_code}): {url}")
        return FetchResult(html=None, from_cache=False, failed=True, status_code=response.status_code)

    return FetchResult(html=None, from_cache=False, failed=True)


# ---- Discovery ----
def discover_book_links(catalogue_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 a")
        if a_tag and a_tag.get("href"):
            links.append(urljoin(catalogue_url, a_tag["href"]))
    return links


def find_next_page_url(catalogue_url: str, html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    if next_link and next_link.get("href"):
        return urljoin(catalogue_url, next_link["href"])
    return None


def discover_all_catalogue_pages(start_url: str) -> list[str]:
    pages = []
    current_url = start_url
    page_num = 1
    while current_url and page_num <= 3:
        cache_filename = f"catalogue-page-{page_num}.html"
        result = fetch_page(current_url, cache_filename)
        if result.failed:
            print(f"FATAL: could not fetch catalogue page {page_num}, stopping discovery")
            break
        pages.append(current_url)
        current_url = find_next_page_url(current_url, result.html)
        page_num += 1
    return pages


def url_to_cache_filename(url: str) -> str:
    slug = url.rstrip("/").split("/")[-2]
    return f"book-{slug}.html"


# ---- Extraction ----
def extract_book_record(book_url: str, html: str, source_page: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("div.product_main")

    title = product.select_one("h1").get_text(strip=True) if product else None

    price_el = product.select_one("p.price_color") if product else None
    price_text = price_el.get_text(strip=True) if price_el else None

    availability_el = product.select_one("p.availability") if product else None
    availability_text = availability_el.get_text(strip=True) if availability_el else None

    rating_el = product.select_one("p.star-rating") if product else None
    rating_text = None
    if rating_el:
        classes = rating_el.get("class", [])
        rating_text = next((c for c in classes if c != "star-rating"), None)

    desc_heading = soup.select_one("#product_description")
    description = None
    if desc_heading:
        desc_p = desc_heading.find_next_sibling("p")
        if desc_p:
            description = desc_p.get_text(strip=True)

    return {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---- Normalize ----
def normalize_record(raw: dict) -> dict:
    price_match = re.search(r"[\d.]+", raw.get("price_text") or "")
    price_gbp = float(price_match.group()) if price_match else None
    rating = RATING_WORDS.get(raw.get("rating_text"))

    return {
        "title": raw["title"],
        "product_url": raw["product_url"],
        "price_gbp": price_gbp,
        "price_text": raw["price_text"],
        "availability_text": raw["availability_text"],
        "rating": rating,
        "description": raw["description"],
        "source_page": raw["source_page"],
        "fetched_at": raw["fetched_at"],
    }


if __name__ == "__main__":
    run_start = datetime.now(timezone.utc)

    start_url = BASE_URL + "catalogue/page-1.html"
    catalogue_pages = discover_all_catalogue_pages(start_url)

    book_link_to_source = {}
    cache_hits = 0
    pages_fetched = 0

    for i, page_url in enumerate(catalogue_pages, start=1):
        cache_filename = f"catalogue-page-{i}.html"
        result = fetch_page(page_url, cache_filename)
        if result.from_cache:
            cache_hits += 1
        else:
            pages_fetched += 1
        links = discover_book_links(page_url, result.html)
        for link in links:
            if link not in book_link_to_source:
                book_link_to_source[link] = page_url

    unique_links = list(book_link_to_source.keys())

    # Stage 5 checkpoint: deliberately add one fake URL to prove failure handling
    if INCLUDE_FAKE_URL_FOR_TESTING and FAKE_BOOK_URL not in unique_links:
        unique_links.append(FAKE_BOOK_URL)
        book_link_to_source[FAKE_BOOK_URL] = "manually added for failure testing"

    valid_records = []
    error_records = []
    failed_pages = 0

    for book_url in unique_links:
        cache_filename = url_to_cache_filename(book_url)
        result = fetch_page(book_url, cache_filename)

        if result.from_cache:
            cache_hits += 1
        elif not result.failed:
            pages_fetched += 1

        if result.failed:
            failed_pages += 1
            error_records.append({
                "product_url": book_url,
                "reason": f"fetch failed, status={result.status_code}"
            })
            continue

        raw = extract_book_record(book_url, result.html, book_link_to_source[book_url])
        normalized = normalize_record(raw)

        try:
            book = Book(**normalized)
            valid_records.append(book.model_dump())
        except ValidationError as e:
            error_records.append({"record": normalized, "reason": str(e)})

    # de-dupe by canonical product_url
    seen = {}
    for r in valid_records:
        seen[r["product_url"]] = r
    final_records = list(seen.values())

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "books.json"), "w", encoding="utf-8") as f:
        json.dump(final_records, f, indent=2, ensure_ascii=False)

    with open(os.path.join(OUTPUT_DIR, "errors.json"), "w", encoding="utf-8") as f:
        json.dump(error_records, f, indent=2, ensure_ascii=False)

    run_end = datetime.now(timezone.utc)
    duration_seconds = (run_end - run_start).total_seconds()

    run_report = {
        "start_time": run_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": round(duration_seconds, 2),
        "pages_fetched": pages_fetched,
        "cache_hits": cache_hits,
        "valid_records": len(final_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages,
    }

    with open(os.path.join(OUTPUT_DIR, "run-report.json"), "w", encoding="utf-8") as f:
        json.dump(run_report, f, indent=2)

    print("\n--- RUN REPORT ---")
    for k, v in run_report.items():
        print(f"  {k}: {v}")