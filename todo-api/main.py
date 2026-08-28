import os
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

#  Database setup 
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    done: bool = False


def create_db_and_seed():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        existing = session.exec(select(Task)).first()
        if not existing:
            session.add(Task(title="Buy milk", done=False))
            session.add(Task(title="Walk the dog", done=False))
            session.add(Task(title="Finish assignment", done=True))
            session.commit()


@app.on_event("startup")
def on_startup():
    create_db_and_seed()


#  Request body models 
class TaskCreate(SQLModel):
    title: Optional[str] = None


class TaskUpdate(SQLModel):
    title: Optional[str] = None
    done: Optional[bool] = None


# Root and health 
@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "3.0",
        "endpoints": ["/tasks"]
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# Read 
@app.get("/tasks")
def get_tasks():
    with Session(engine) as session:
        tasks = session.exec(select(Task)).all()
        return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task


# Create 
@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    with Session(engine) as session:
        new_task = Task(title=task.title, done=False)
        session.add(new_task)
        session.commit()
        session.refresh(new_task)
        return new_task


# Update & Delete
@app.put("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if update.title is not None:
            if not update.title.strip():
                raise HTTPException(status_code=400, detail="Title cannot be empty")
            task.title = update.title
        if update.done is not None:
            task.done = update.done

        session.add(task)
        session.commit()
        session.refresh(task)
        return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        session.delete(task)
        session.commit()
        return
