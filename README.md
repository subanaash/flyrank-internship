# Task API

A simple CRUD API for managing a to-do list, built with FastAPI. Tasks are stored in memory (no database) and reset when the server restarts.

## What this is

This project implements the four CRUD operations (Create, Read, Update, Delete) over a list of tasks, with input validation, correct HTTP status codes, and interactive documentation via Swagger UI.

## How to run it

1. Clone the repo and enter the folder:
   ```
   git clone https://github.com/subanaash/todo-api.git
   cd todo-api
   ```

2. Create a virtual environment and activate it:
   ```
   python3 -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install fastapi uvicorn
   ```

4. Run the server:
   ```
   uvicorn main:app --reload
   ```

5. Open your browser to `http://127.0.0.1:8000`

## Endpoints

| Method | Endpoint | Description | Success Code | Error Code |
|--------|----------|--------------|--------------|------------|
| GET | `/` | API info | 200 | — |
| GET | `/health` | Health check | 200 | — |
| GET | `/tasks` | List all tasks | 200 | — |
| GET | `/tasks/{id}` | Get one task | 200 | 404 if not found |
| POST | `/tasks` | Create a task | 201 | 400 if title missing/empty |
| PUT | `/tasks/{id}` | Update a task | 200 | 400 invalid body, 404 if not found |
| DELETE | `/tasks/{id}` | Delete a task | 204 | 404 if not found |

## Example: curl output

```
$ curl.exe -i http://127.0.0.1:8000/tasks
HTTP/1.1 200 OK
date: Tue, 04 Aug 2026 12:00:35 GMT
server: uvicorn
content-length: 135
content-type: application/json

[{"id":1,"title":"Buy milk","done":true},{"id":2,"title":"Walk the dog","done":false},{"id":3,"title":"Finish assignment","done":true}]
```

## Swagger UI

Interactive API docs are available at `http://127.0.0.1:8000/docs` (built in automatically with FastAPI).


<img width="1507" height="932" alt="Screenshot 2026-08-04 173739" src="https://github.com/user-attachments/assets/d2723e72-b81b-45d8-bfe6-ca73db48993d" />
<img width="547" height="881" alt="Screenshot 2026-08-04 174414" src="https://github.com/user-attachments/assets/3246b52f-9761-4b44-aea8-d15a11cc9316" />
<img width="1021" height="206" alt="Screenshot 2026-08-04 174559" src="https://github.com/user-attachments/assets/fb14b404-5beb-468d-a5dc-ee5079174604" />
<img width="597" height="785" alt="Screenshot 2026-08-04 181437" src="https://github.com/user-attachments/assets/2895b0cf-c323-4fab-9ab2-193fd98a6c54" />


## Database (Week 3)

### Why SQLite
SQLite was chosen because it requires no separate database server — it's a single file (`tasks.db`) that gets created automatically the first time the app runs. This makes it ideal for a small project like this: no setup, no configuration, and easy to inspect directly with a tool like DB Browser for SQLite.

### Where the database lives
The database file is created at the project root: `todo-api/tasks.db`. It's excluded from version control via `.gitignore` — it's local to whoever runs the project and gets recreated automatically on first run.

### Example SQL query
Opened `tasks.db` in DB Browser for SQLite and ran:
```sql
SELECT * FROM task;
```
This returned every task currently stored in the database, confirming the API and the database stay in sync — any change made through the API (or directly in the database) is immediately reflected in the other.

### Database viewer screenshot
<img width="318" height="522" alt="image" src="https://github.com/user-attachments/assets/ca93e5d1-b00e-4101-93aa-87f927105cbc" />



## Notes

Data is stored in memory only. Restarting the server resets tasks back to the original 3 seed items. This is intentional for this stage of the project; persistence will be added in a later assignment.

## AI vs me

**My prompt:** "Build a CRUD API in Python using FastAPI for managing a to-do list. Endpoints: GET /tasks (list all, 200), GET /tasks/{id} (get one, 200, or 404 if not found), POST /tasks (create, 201, requires a title, returns 400 if title is missing or empty), PUT /tasks/{id} (update title and/or done, 200, or 404 if not found, 400 if title is empty), DELETE /tasks/{id} (delete, 204, or 404 if not found). Data should be stored in memory (a Python list), not a database — it resets on restart. Include Swagger UI documentation, which FastAPI provides automatically at /docs."

**What the AI did better:**
- Its validation error messages are more structured/verbose (using Pydantic's value_error type with a clear loc path), which could be easier to parse programmatically than my simpler {"detail": "Title is required"}.

**What it got wrong or quietly skipped:**
- It never implemented a root Get /  endpoint. My prompt didn't explicitly ask for one, but it's a gap — my own API returns API info there, and I only noticed the AI's version was missing it when I got a 404 testing the base URL.
- Its 404 error message is generic ("Task not found") instead of including the specific id, like mine does ("Task 4 not found") ; a small but useful debugging detail my version has that theirs doesn't.

**What my prompt forgot to specify:**
- I didn't specify the exact shape of the error response body, so the AI defaulted to Pydantic's built-in validation error format instead of a simple custom message like mine.
- I didn't mention the root / endpoint at all, which is why the AI skipped it entirely , a case of the AI doing exactly what I asked, not what I actually needed.

**One rematch:** Adding a line specifying "Include a GET / endpoint that returns API name, version, and list of endpoints" and "Return errors as a simple {\"detail\": \"<message>\"} JSON object, not a Pydantic validation error" would fix both gaps found above.


## Postgres + Docker (Week 4)

### What changed
The app moved from SQLite to Postgres, running in Docker with a persistent volume. The service and route code did not change at all — only the database connection (now read from `.env`) and the underlying engine changed. This proves the storage layer is properly decoupled from the API layer.

### How to run it
1. Copy `.env.example` to `.env` and fill in your own values (or use the defaults for local dev):
   ```
   cp .env.example .env
   ```

2. Start everything (Postgres + the app) with one command:
   ```
   docker compose up
   ```

3. Open your browser to `http://localhost:8000`

The first time this runs, Postgres creates its data volume and the app automatically creates the `task` table and seeds it with 3 example tasks.

### Environment variables
`.env` (gitignored) holds the real connection details. `.env.example` (committed) shows the expected shape without real secrets:
```
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=yourdbname
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/yourdbname
```

### Proving persistence
1. Created a new task via POST /tasks (`"Persistence test"`, id 4).
2. Ran `docker compose down` — this fully stops and removes both the app and database containers.
3. Ran `docker compose up` again — both containers rebuilt from scratch.
4. Called `GET /tasks` — the "Persistence test" task (id 4) was still present, confirming data survived a complete container restart thanks to the named Docker volume (`todo-pgdata`).

**docker ps output:**
<img width="1050" height="252" alt="Screenshot 2026-08-11 165848" src="https://github.com/user-attachments/assets/9420ef6b-bd32-4bd4-a25a-98b1483499f6" />

**Persistence proof — GET /tasks:**
<img width="257" height="341" alt="Screenshot 2026-08-11 165913" src="https://github.com/user-attachments/assets/77daee6c-1610-4577-8012-e072f0e01c6e" />



### Architecture note
Swapping SQLite for Postgres only required changing where the database engine gets its connection string — the `Task` model, all route handlers, and all business logic in `main.py` stayed identical. This is the layering the assignment is built to prove: the API describes *what* the app does, the database describes *where* it stores data, and those two concerns don't need to know about each other.




