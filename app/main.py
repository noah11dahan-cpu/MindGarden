from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()
DB_URL = os.getenv("DB_URL", "sqlite:///app.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

app = FastAPI(title="MindGarden API", version="0.1.0")

class HealthStatus(BaseModel):
    status: str
    db_ok: bool

@app.get("/healthz", response_model=HealthStatus)
def healthz():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return HealthStatus(status="ok", db_ok=True)
    except Exception:
        return HealthStatus(status="ok", db_ok=False)
