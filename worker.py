from celery import Celery
from agent.core import run_agent

celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

@celery_app.task(bind=True)
def run_agent_task(self, task, start_url):
    return run_agent(
        task=task,
        start_url=start_url,
        headless=True,
        task_id=self.request.id,
    )