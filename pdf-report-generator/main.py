import sqlite3
import os
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from report_data import get_report_data
from render_pdf import get_all_books, build_html, render_pdf

DB_PATH = "report.db"
REPORTS_DIR = "reports"

app = FastAPI()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_reports_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


init_reports_table()
os.makedirs(REPORTS_DIR, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports", status_code=201)
def create_report(force: bool = False):
    conn = get_db()

    if not force:
        today = date.today().isoformat()
        existing = conn.execute(
            "SELECT * FROM reports WHERE created_at = ? ORDER BY id DESC LIMIT 1",
            (today,),
        ).fetchone()

        if existing:
            conn.close()
            return JSONResponse(
                status_code=200,
                content={"id": existing["id"], "file": f"/reports/{existing['id']}/file"},
            )

    report_data = get_report_data()
    all_books = get_all_books()
    html = build_html(report_data, all_books)

    cursor = conn.execute(
        "INSERT INTO reports (path, created_at) VALUES (?, ?)",
        ("", date.today().isoformat()),
    )
    report_id = cursor.lastrowid

    file_path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")
    render_pdf(html, file_path)

    conn.execute("UPDATE reports SET path = ? WHERE id = ?", (file_path, report_id))
    conn.commit()
    conn.close()

    return {"id": report_id, "file": f"/reports/{report_id}/file"}


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "file": f"/reports/{row['id']}/file",
    }


@app.get("/reports/{report_id}/file")
def get_report_file(report_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()

    if not row or not os.path.exists(row["path"]):
        raise HTTPException(status_code=404, detail=f"Report {report_id} file not found")

    return FileResponse(row["path"], media_type="application/pdf", filename=f"report-{report_id}.pdf")