# PDF Report Generator

Queries a small SQLite database with SQL aggregation, renders the results into a real PDF report using a headless browser, and serves the finished file by link — no background jobs required.

## Dataset

Option B (the bookstore): reused the 60 validated book records collected in Week 5's scraper assignment (`books.json`), loaded into a `books` table in `report.db`.

## How to run it

1. Clone the repo and enter the folder:
   ```
   git clone https://github.com/subanaash/flyrank-internship.git
   cd flyrank-internship/pdf-report-generator
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install fastapi uvicorn playwright
   python -m playwright install chromium
   ```

3. Seed the database (place your own `books.json` in this folder first, or use the included one):
   ```
   python seed.py
   ```

4. Run the API:
   ```
   uvicorn main:app --reload
   ```

## Aggregation SQL

```sql
-- Total books
SELECT COUNT(*) FROM books;

-- Average price
SELECT AVG(price) FROM books;

-- Top 5 most expensive
SELECT title, price FROM books ORDER BY price DESC LIMIT 5;

-- Books per star rating
SELECT rating, COUNT(*) FROM books GROUP BY rating ORDER BY rating;
```

## Generate and download a report

```
curl -i -X POST http://localhost:8000/reports
```
Returns `201` with `{"id": 1, "file": "/reports/1/file"}` after a visible pause (the whole pipeline runs inside the request).

```
curl -o my-report.pdf http://localhost:8000/reports/1/file
```
Downloads the real PDF.

## Stage 4 note: when this should become a background job

Right now, `POST /reports` blocks for a few seconds while it queries, renders, and saves — acceptable for one user clicking one button. I'd move this into a background job (using the Inngest pattern from an earlier assignment) once report generation regularly takes long enough to feel like a stuck request, or once multiple users could trigger it at the same time — at that point, the endpoint should return `202 Accepted` immediately and let the client poll `/reports/:id` for a `pending`/`done` status instead of holding the connection open.

## Stage 5 notes: idempotency

**What this protects against:** a user double-clicking "Generate Report" (or a flaky network causing a client to retry) would otherwise silently create duplicate files and duplicate database rows for the exact same request.

**Real-world example:** an e-commerce checkout button that isn't idempotent can charge a customer's card twice if they click "Pay" twice while the first request is still processing — the same class of bug as generating two reports from one click, just with real financial cost.

**Proof:** two rapid `POST /reports` calls on the same day both returned `200` (not `201`) with the same `id: 1`. Passing `?force=true` correctly bypassed the check and created a new report (`id: 2`) instead.

## page 1 of a generated report

<img width="598" height="831" alt="image" src="https://github.com/user-attachments/assets/f63c69ee-d339-4605-baf9-2f73087301aa" />
