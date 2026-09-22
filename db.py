from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "postgresql://agent_user:agent_pass@localhost:5432/agent_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(String, primary_key=True)          # the run_id / task_id
    task = Column(Text, nullable=False)
    start_url = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="incomplete")
    final_answer = Column(Text, nullable=True)
    steps = Column(JSON, nullable=True)             # full list of step dicts, stored as JSON
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Creates the task_runs table if it doesn't already exist."""
    Base.metadata.create_all(bind=engine)