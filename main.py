from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from worker import run_agent_task
import redis.asyncio as aioredis
import asyncio
import os
import json

from agent.core import run_agent
from db import SessionLocal, TaskRun

app = FastAPI(title="Browser AI Agent API")

# CORS is wide open for local development. Restrict allow_origins to the deployed
# frontend's actual domain before exposing this publicly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    task: str
    start_url: str


@app.get("/")
def root():
    return {"message": "Browser AI Agent API is running"}


@app.post("/run-task")
def run_task(request: TaskRequest):
    """Enqueues the task to run in a background Celery worker and returns
    immediately with a task_id the client can use to check status/result."""
    job = run_agent_task.delay(request.task, request.start_url)
    return {"task_id": job.id}


@app.get("/task-status/{task_id}")
def task_status(task_id: str):
    """Returns the current status of a background task, and its result once ready."""
    result = run_agent_task.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@app.get("/reports")
def list_reports():
    session = SessionLocal()
    runs = session.query(TaskRun).order_by(TaskRun.created_at.desc()).all()
    session.close()

    return {
        "reports": [
            {
                "run_id": r.id,
                "task": r.task,
                "status": r.status,
                "final_answer": r.final_answer
            }
            for r in runs
        ]
    }


@app.get("/reports/{run_id}")
def get_report(run_id: str):
    session = SessionLocal()
    run = session.query(TaskRun).filter(TaskRun.id == run_id).first()
    session.close()

    if not run:
        return {"error": "Report not found"}

    return {
        "task": run.task,
        "start_url": run.start_url,
        "status": run.status,
        "final_answer": run.final_answer,
        "steps": run.steps,
    }

@app.websocket("/ws/{task_id}")
async def task_updates_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()

    r = aioredis.Redis(
        host="localhost",
        port=6379,
        db=0
    )

    pubsub = r.pubsub()

    await pubsub.subscribe(f"task_updates:{task_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(
                    message["data"].decode()
                )
    except Exception:
        pass
    finally:
        await pubsub.unsubscribe(
            f"task_updates:{task_id}"
        )
        await websocket.close()