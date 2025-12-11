from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv("DB_URL", "sqlite:///app.db")
engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})

with engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS __init_check__(id INTEGER PRIMARY KEY, note TEXT)"))
    conn.execute(text("INSERT INTO __init_check__(note) VALUES ('ok')"))

print("SQLite write OK:", db_url)
