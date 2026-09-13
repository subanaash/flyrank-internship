import sqlite3
import json
import os

DB_PATH = "report.db"
BOOKS_JSON_PATH = "books.json"  # copy your Week 5 scraper's books.json into this folder


def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY,
            title TEXT,
            price REAL,
            rating INTEGER,
            url TEXT
        )
    """)

    # Delete all rows first, so running this twice leaves exactly one clean copy
    cursor.execute("DELETE FROM books")

    if not os.path.exists(BOOKS_JSON_PATH):
        print(f"ERROR: {BOOKS_JSON_PATH} not found. Copy your Week 5 books.json into this folder first.")
        return

    with open(BOOKS_JSON_PATH, "r", encoding="utf-8") as f:
        books = json.load(f)

    for book in books:
        cursor.execute(
            "INSERT INTO books (id, title, price, rating, url) VALUES (?, ?, ?, ?, ?)",
            (
                book.get("id"),
                book.get("title"),
                book.get("price_gbp"),
                book.get("rating"),
                book.get("product_url"),
            ),
        )

    conn.commit()

    count = cursor.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    print(f"Seeded {count} books into {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    seed()