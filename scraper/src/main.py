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


# ---- Fetch / cache ----
def fetch_page(url: str, cache_filename: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_filename} ({len(html)} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url}: status {response.status_code}")

    response.encoding = "utf-8"
    html = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"FETCH: {cache_filename} ({len(html)} bytes, status {response.status_code})")
    time.sleep(DELAY)
    return html


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
        html = fetch_page(current_url, cache_filename)
        pages.append(current_url)
        current_url = find_next_page_url(current_url, html)
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
    start_url = BASE_URL + "catalogue/page-1.html"
    catalogue_pages = discover_all_catalogue_pages(start_url)

    book_link_to_source = {}
    for i, page_url in enumerate(catalogue_pages, start=1):
        cache_filename = f"catalogue-page-{i}.html"
        html = fetch_page(page_url, cache_filename)
        links = discover_book_links(page_url, html)
        for link in links:
            if link not in book_link_to_source:
                book_link_to_source[link] = page_url

    unique_links = list(book_link_to_source.keys())

    valid_records = []
    error_records = []

    for book_url in unique_links:
        cache_filename = url_to_cache_filename(book_url)
        html = fetch_page(book_url, cache_filename)
        raw = extract_book_record(book_url, html, book_link_to_source[book_url])
        normalized = normalize_record(raw)

        try:
            book = Book(**normalized)
            valid_records.append(book.model_dump())
        except ValidationError as e:
            error_records.append({"record": normalized, "reason": str(e)})

    # de-dupe by canonical product_url, keep first occurrence
    seen = {}
    for r in valid_records:
        seen[r["product_url"]] = r
    final_records = list(seen.values())

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "books.json"), "w", encoding="utf-8") as f:
        json.dump(final_records, f, indent=2, ensure_ascii=False)

    with open(os.path.join(OUTPUT_DIR, "errors.json"), "w", encoding="utf-8") as f:
        json.dump(error_records, f, indent=2, ensure_ascii=False)

    print(f"\nvalid_records={len(final_records)}")
    print(f"error_records={len(error_records)}")
    all_https = all(r["product_url"].startswith("https://") for r in final_records)
    all_numeric_price = all(isinstance(r["price_gbp"], float) for r in final_records)
    print(f"all_urls_https={all_https}")
    print(f"all_prices_numeric={all_numeric_price}")