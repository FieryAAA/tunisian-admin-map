from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
from datetime import date
from sqlmodel import Session, create_engine, select
from .db.queries import get_org_snapshot

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/marsad")
engine = create_engine(DATABASE_URL)

app = FastAPI(title="Marsad Al-Idara API")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/snapshot")
def read_snapshot(date: str = Query(...)):
    """Full org chart at a specific date."""
    # Note: Wrap standard connection if using the queries.py logic or use SQLModel
    # For now, we return a mock or call the query function if it's integrated
    try:
        # In actual implementation, pass the engine connection
        snapshot = get_org_snapshot(engine.raw_connection(), date)
        return snapshot
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/timeline")
def read_timeline(from_year: int = Query(...), to_year: int = Query(...)):
    """All events in a date range."""
    # Placeholder for chronological event query
    return {"events": []}

@app.get("/api/persons/{person_id}")
def read_person(person_id: str):
    """Person profile and full career timeline."""
    return {"id": person_id, "name": "Fake Person", "career": []}

@app.get("/api/institutions/{inst_id}")
def read_institution(inst_id: str):
    """Institution profile and full history."""
    return {"id": inst_id, "name": "Fake Ministry", "history": []}

@app.get("/api/search")
def search(q: str, type: str = "semantic"):
    """Search persons + decrees."""
    return {"results": []}

@app.get("/api/stats")
def read_stats():
    """ministry count over time, top tenures, etc."""
    return {"stats": {}}

@app.get("/")
def health_check():
    return {"status": "ok"}
