from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional

app = FastAPI(title="To-Do List API")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Convert Pydantic's default 422 into 400, as required by the API spec
    errors = [
        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=400, content={"detail": errors})

# In-memory storage
tasks: list[dict] = []
next_id = 1


class TaskCreate(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be empty")
        return v


class Task(BaseModel):
    id: int
    title: str
    done: bool = False


def find_task(task_id: int) -> Optional[dict]:
    return next((t for t in tasks if t["id"] == task_id), None)


@app.get("/tasks", response_model=list[Task], status_code=200)
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}", response_model=Task, status_code=200)
def get_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate):
    global next_id
    task = {"id": next_id, "title": payload.title.strip(), "done": False}
    tasks.append(task)
    next_id += 1
    return task


@app.put("/tasks/{task_id}", response_model=Task, status_code=200)
def update_task(task_id: int, payload: TaskUpdate):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if payload.title is not None:
        task["title"] = payload.title.strip()
    if payload.done is not None:
        task["done"] = payload.done
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    tasks.remove(task)
    return None
