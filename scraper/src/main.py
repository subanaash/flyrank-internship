import os
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = "cache"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/subanaash/flyrank-internship)"
TIMEOUT = 10
DELAY = 0.5  # seconds between real requests


def fetch_page(url: str, cache_filename: str) -> str:
    """Fetch a page politely, using a cache to avoid hitting the site repeatedly."""
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

    html = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"FETCH: {cache_filename} ({len(html)} bytes, status {response.status_code})")
    time.sleep(DELAY)  # be polite, only after a real network request
    return html


def discover_book_links(catalogue_url: str, html: str) -> list[str]:
    """Extract absolute book URLs from a catalogue page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 a")
        if a_tag and a_tag.get("href"):
            absolute_url = urljoin(catalogue_url, a_tag["href"])
            links.append(absolute_url)
    return links


def find_next_page_url(catalogue_url: str, html: str) -> str | None:
    """Find the 'next' page link, if one exists."""
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")
    if next_link and next_link.get("href"):
        return urljoin(catalogue_url, next_link["href"])
    return None


def discover_all_catalogue_pages(start_url: str) -> list[str]:
    """Follow 'next' links to find all catalogue page URLs (stops after 3 for this assignment)."""
    pages = []
    current_url = start_url
    page_num = 1

    while current_url and page_num <= 3:
        cache_filename = f"catalogue-page-{page_num}.html"
        html = fetch_page(current_url, cache_filename)
        pages.append(current_url)

        next_url = find_next_page_url(current_url, html)
        current_url = next_url
        page_num += 1

    return pages


if __name__ == "__main__":
    start_url = BASE_URL + "catalogue/page-1.html"
    catalogue_pages = discover_all_catalogue_pages(start_url)

    all_links = []
    for i, page_url in enumerate(catalogue_pages, start=1):
        cache_filename = f"catalogue-page-{i}.html"
        html = fetch_page(page_url, cache_filename)
        links = discover_book_links(page_url, html)
        all_links.extend(links)

    unique_links = list(dict.fromkeys(all_links))  # dedupe, preserve order

    print(f"catalogue_pages={len(catalogue_pages)}")
    print(f"discovered={len(all_links)}")
    print(f"unique_urls={len(unique_links)}")