import os
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = "cache"
OUTPUT_DIR = "output"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/subanaash/flyrank-internship)"
TIMEOUT = 10
DELAY = 0.5


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
    """Turn a book URL's slug into a safe cache filename."""
    slug = url.rstrip("/").split("/")[-2]  # e.g. a-light-in-the-attic_1000
    return f"book-{slug}.html"


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
    print(f"catalogue_pages={len(catalogue_pages)}")
    print(f"unique_urls={len(unique_links)}")

    records = []
    for book_url in unique_links:
        cache_filename = url_to_cache_filename(book_url)
        html = fetch_page(book_url, cache_filename)
        record = extract_book_record(book_url, html, book_link_to_source[book_url])
        records.append(record)

    print(f"detail_pages={len(records)}")
    print("\nSample record:")
    for k, v in records[0].items():
        print(f"  {k}: {v}")