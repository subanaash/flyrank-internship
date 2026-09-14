import sqlite3
from datetime import date
from playwright.sync_api import sync_playwright
from report_data import get_report_data

DB_PATH = "report.db"


def get_all_books():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rows = cursor.execute("SELECT title, price, rating, url FROM books ORDER BY id").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def build_html(report: dict, all_books: list) -> str:
    today = date.today().strftime("%B %d, %Y")

    top5_rows = "".join(
        f"<tr><td>{b['title']}</td><td>£{b['price']:.2f}</td></tr>"
        for b in report["top_5_expensive"]
    )

    rating_rows = "".join(
        f"<tr><td>{r['rating']} star</td><td>{r['count']}</td></tr>"
        for r in report["books_per_rating"]
    )

    all_books_rows = "".join(
        f"<tr><td>{b['title']}</td><td>£{b['price']:.2f}</td><td>{b['rating']} star</td></tr>"
        for b in all_books
    )

    return f"""
    <html>
    <head>
    <style>
        body {{ font-family: sans-serif; color: #1A1A1A; padding: 20px; }}
        h1 {{ font-size: 22px; }}
        h2 {{ font-size: 16px; margin-top: 24px; }}
        p.date {{ color: #666; font-size: 12px; }}
        .totals {{ display: flex; gap: 24px; margin: 16px 0; }}
        .totals div {{ border: 1px solid #ccc; border-radius: 8px; padding: 12px 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
        th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 12px; }}
        thead {{ display: table-header-group; }}
        tr {{ break-inside: avoid; }}
    </style>
    </head>
    <body>
        <h1>Book Catalogue Report</h1>
        <p class="date">Generated on {today}</p>

        <div class="totals">
            <div><strong>Total books:</strong> {report['total_books']}</div>
            <div><strong>Average price:</strong> £{report['average_price']}</div>
        </div>

        <h2>Top 5 Most Expensive Books</h2>
        <table>
            <thead><tr><th>Title</th><th>Price</th></tr></thead>
            <tbody>{top5_rows}</tbody>
        </table>

        <h2>Books per Star Rating</h2>
        <table>
            <thead><tr><th>Rating</th><th>Count</th></tr></thead>
            <tbody>{rating_rows}</tbody>
        </table>

        <h2>All Books</h2>
        <table>
            <thead><tr><th>Title</th><th>Price</th><th>Rating</th></tr></thead>
            <tbody>{all_books_rows}</tbody>
        </table>
    </body>
    </html>
    """


def render_pdf(html: str, output_path: str):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=output_path, format="A4", print_background=True)
        browser.close()


if __name__ == "__main__":
    report = get_report_data()
    all_books = get_all_books()
    html = build_html(report, all_books)
    render_pdf(html, "reports/test.pdf")
    print("PDF generated at reports/test.pdf")