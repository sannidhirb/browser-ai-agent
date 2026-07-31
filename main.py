from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json

from agent.core import run_agent

app = FastAPI(title="Browser AI Agent API")

# Allow the future React frontend (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local development; we'll tighten this later
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
    """Runs the agent synchronously and returns the full report once done."""
    report = run_agent(
        task=request.task,
        start_url=request.start_url,
        headless=True,  # no visible browser window when running as a server
    )
    return report


@app.get("/reports")
def list_reports():
    """Returns a list of all past task runs, most recent first."""
    if not os.path.exists("reports"):
        return {"reports": []}

    run_ids = sorted(os.listdir("reports"), reverse=True)
    summaries = []
    for run_id in run_ids:
        report_path = f"reports/{run_id}/report.json"
        if os.path.exists(report_path):
            with open(report_path) as f:
                data = json.load(f)
            summaries.append({
                "run_id": run_id,
                "task": data.get("task"),
                "status": data.get("status"),
                "final_answer": data.get("final_answer"),
            })
    return {"reports": summaries}


@app.get("/reports/{run_id}")
def get_report(run_id: str):
    """Returns the full report for one specific run."""
    report_path = f"reports/{run_id}/report.json"
    if not os.path.exists(report_path):
        return {"error": "Report not found"}
    with open(report_path) as f:
        return json.load(f)