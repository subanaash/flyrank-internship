import sqlite3
import json

DB_PATH = "report.db"


def get_report_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Total number of books
    total_books = cursor.execute("SELECT COUNT(*) AS count FROM books").fetchone()["count"]

    # Average price
    average_price = cursor.execute("SELECT AVG(price) AS avg_price FROM books").fetchone()["avg_price"]

    # Top 5 most expensive books
    top_5_expensive = cursor.execute("""
        SELECT title, price
        FROM books
        ORDER BY price DESC
        LIMIT 5
    """).fetchall()
    top_5_expensive = [dict(row) for row in top_5_expensive]

    # Number of books per star rating
    books_per_rating = cursor.execute("""
        SELECT rating, COUNT(*) AS count
        FROM books
        GROUP BY rating
        ORDER BY rating
    """).fetchall()
    books_per_rating = [dict(row) for row in books_per_rating]

    conn.close()

    return {
        "total_books": total_books,
        "average_price": round(average_price, 2) if average_price else 0,
        "top_5_expensive": top_5_expensive,
        "books_per_rating": books_per_rating,
    }


if __name__ == "__main__":
    report = get_report_data()
    print(json.dumps(report, indent=2))