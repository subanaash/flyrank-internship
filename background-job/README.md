# Your First Background Job

A small API that demonstrates the three ways work can start: request/response, background job triggered by an event, and a cron job triggered by the clock alone — all using Inngest.

## How to run it

1. Clone the repo and enter the folder:
   ```
   git clone https://github.com/subanaash/flyrank-internship.git
   cd flyrank-internship/background-job
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install fastapi uvicorn inngest
   ```

3. Start the API:
   ```
   uvicorn main:app --reload --port 8000
   ```

4. In a second terminal, start the Inngest Dev Server:
   ```
   npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
   ```

5. Dashboard at `http://localhost:8288`.

## Endpoints and functions

| Type | Name | Trigger | What it does |
|---|---|---|---|
| Endpoint | `GET /health` | HTTP | Health check |
| Endpoint | `POST /reports` | HTTP | Accepts a topic, returns `202` instantly, triggers a background job |
| Endpoint | `GET /reports/:id` | HTTP | Polls report status: `pending` → `done` + result; unknown id → `404` |
| Function | `say-hello` | Event `test/hello` | Simple sleep-then-return, used to confirm Inngest is wired up |
| Function | `make-report` | Event `report/requested` | Sleeps 8s (stand-in for slow work), builds the result, retries twice on failure |
| Function | `heartbeat` | Cron `* * * * *` | Runs every minute, logs a summary of pending/done/failed reports — no request involved |

## Proof: 202 then poll

```
$ curl -i -X POST http://localhost:8000/reports -H "Content-Type: application/json" -d "{\"topic\":\"cats\"}"
HTTP/1.1 202 Accepted
{"id":"a1b2c3...", "status":"pending"}
# responded in 481ms

$ curl -i http://localhost:8000/reports/a1b2c3...
{"id":"a1b2c3...", "topic":"cats", "status":"pending"}

# ~10 seconds later
$ curl -i http://localhost:8000/reports/a1b2c3...
{"id":"a1b2c3...", "topic":"cats", "status":"done", "result":"Report on 'cats': this is a placeholder result after 8 seconds of work."}
```

## Stage 3 note: why some errors deserve a retry and others don't

A missing or invalid `topic` is rejected immediately with a `422` and no job is ever created — retrying a request that was wrong from the start would just fail the same way again. A `topic` of `"fail"` represents a job that started correctly but hit a real failure mid-run (a flaky dependency, a timeout) — that's exactly the kind of failure a retry can plausibly fix, so Inngest retries it automatically with backoff before giving up.

## Stage 4 note: cron expressions

- Every day at 08:00: `0 8 * * *`
- Every Sunday at 22:00: `0 22 * * 0`

(Built and verified on crontab.guru.)

## Dashboard screenshot
<img width="1427" height="347" alt="Screenshot 2026-09-14 092458" src="https://github.com/user-attachments/assets/d68c35cf-5155-4856-a3b6-a11bd612b09a" />

<img width="1657" height="532" alt="Screenshot 2026-09-14 092549" src="https://github.com/user-attachments/assets/9f0adeee-c268-423d-a8ae-af8ff7815b2c" />
