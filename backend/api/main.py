import sys
import logging
from pathlib import Path

# Allow importing from backend/db/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from db.queries import get_org_snapshot

logger = logging.getLogger(__name__)

app = FastAPI(title="Marsad Al-Idara API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

DB_CONFIG = {
    "dbname":   os.getenv("POSTGRES_DB",       "marsad"),
    "user":     os.getenv("POSTGRES_USER",     "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "password"),
    "host":     os.getenv("POSTGRES_HOST",     "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", "5432")),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# ---------------------------------------------------------------------------
# Mock data — used as fallback when the database is empty (pre-pipeline)
# ---------------------------------------------------------------------------

MOCK_INSTITUTIONS = [
    { "id": "1",     "name_fr": "Presidency of the Republic",              "type": "sov",      "parent_id": None,   "person": {"id": "p1",   "name_fr": "Kais Saied"},          "description": "Head of State and Supreme Commander of the Armed Forces." },
    { "id": "2",     "name_fr": "Presidency of the Government",            "type": "ministry", "parent_id": "1",    "person": {"id": "p2",   "name_fr": "Ahmed Hachani"},        "description": "Lead executive body responsible for policy implementation." },
    { "id": "3",     "name_fr": "Ministry of Interior",                    "type": "ministry", "parent_id": "2",    "person": {"id": "p3",   "name_fr": "Kamel Feki"},           "description": "In charge of internal security, local government, and civil protection." },
    { "id": "3-1",   "name_fr": "Central Directorate of Public Security",  "type": "agency",   "parent_id": "3",    "person": {"id": "p31",  "name_fr": "Moncef Sassi"},         "description": "Oversees national security operations and police coordination." },
    { "id": "3-2",   "name_fr": "Regional Directorate of Interior - Sousse","type": "agency",  "parent_id": "3",    "person": {"id": "p32",  "name_fr": "Fethi Belhaj"},         "description": "Regional administrative branch for the Sousse governorate." },
    { "id": "3-3",   "name_fr": "Governorate of Tunis",                    "type": "agency",   "parent_id": "3",    "person": {"id": "p33",  "name_fr": "Kamal Fekih (Governor)"},"description": "Local executive authority for the capital." },
    { "id": "4",     "name_fr": "Ministry of Justice",                     "type": "ministry", "parent_id": "2",    "person": {"id": "p4",   "name_fr": "Leila Jaffel"},         "description": "Oversees the judicial system and legal affairs." },
    { "id": "4-1",   "name_fr": "Court of First Instance - Tunis",         "type": "court",    "parent_id": "4",    "person": {"id": "p41",  "name_fr": "Taher Ben Amor"},       "description": "Primary judicial body for the Tunis district." },
    { "id": "5",     "name_fr": "Ministry of Foreign Affairs",             "type": "ministry", "parent_id": "1",    "person": {"id": "p5",   "name_fr": "Nabil Ammar"},          "description": "Manages international relations and diplomacy." },
    { "id": "5-1",   "name_fr": "Directorate of Consular Affairs",         "type": "agency",   "parent_id": "5",    "person": {"id": "p51",  "name_fr": "Samia Laribi"},         "description": "In charge of visas and citizen services abroad." },
    { "id": "7",     "name_fr": "Ministry of Finance",                     "type": "ministry", "parent_id": "2",    "person": {"id": "p7",   "name_fr": "Sihem Boughdiri"},      "description": "Financial planning, tax collection, and budget management." },
    { "id": "7-1",   "name_fr": "General Directorate of Taxes",            "type": "agency",   "parent_id": "7",    "person": {"id": "p71",  "name_fr": "Mohamed Ridha"},        "description": "Responsible for tax policy and collection." },
    { "id": "7-2",   "name_fr": "Regional Tax Office - Sfax",              "type": "agency",   "parent_id": "7-1",  "person": {"id": "p72",  "name_fr": "Anis Mahjoubi"},        "description": "Regional tax collection branch for Sfax." },
    { "id": "12",    "name_fr": "Ministry of Agriculture",                 "type": "ministry", "parent_id": "2",    "person": {"id": "p12",  "name_fr": "Abdelmonem Belati"},    "description": "Agricultural policy, water resources, and fisheries." },
    { "id": "12-1",  "name_fr": "CRDA - Béja",                             "type": "regional", "parent_id": "12",   "person": {"id": "p121", "name_fr": "Ridha Touiti"},         "description": "Local implementation of agricultural development plans in Béja." },
    { "id": "13",    "name_fr": "Ministry of Health",                      "type": "ministry", "parent_id": "2",    "person": {"id": "p13",  "name_fr": "Ali Mrabet"},           "description": "Public health services and medical regulation." },
    { "id": "13-1",  "name_fr": "National Agency for Sanitary Control",    "type": "agency",   "parent_id": "13",   "person": {"id": "p131", "name_fr": "Karem Ben Ismail"},     "description": "Food and drug safety regulator." },
    { "id": "13-2",  "name_fr": "Regional Directorate of Health - Tunis",  "type": "regional", "parent_id": "13",   "person": {"id": "p132", "name_fr": "Sami Barkia"},          "description": "Oversees hospitals and clinics in the capital region." },
    { "id": "14",    "name_fr": "Ministry of Education",                   "type": "ministry", "parent_id": "2",    "person": {"id": "p14",  "name_fr": "Saloua Abassi"},        "description": "Primary and secondary education management." },
    { "id": "14-1",  "name_fr": "Regional Directorate of Education - Nabeul","type": "regional","parent_id": "14",  "person": {"id": "p141", "name_fr": "Hedi Slim"},            "description": "Manages schools and educational staff in the Nabeul governorate." },
    { "id": "14-1-1","name_fr": "Service of Human Resources - Nabeul",     "type": "service",  "parent_id": "14-1", "person": {"id": "p1411","name_fr": "Amel Rezgui"},          "description": "Handles teacher assignments and payroll for the region." },
    { "id": "14-2",  "name_fr": "Regional Directorate of Education - Bizerte","type": "regional","parent_id": "14", "person": {"id": "p142", "name_fr": "Mounir Lassoued"},      "description": "Manages schools and educational staff in the Bizerte governorate." },
]

MOCK_PERSONS = {
    "p1":   {"id": "p1",   "name_fr": "Kais Saied",        "role": "President",          "history": [{"date": "2019-10-23", "event": "Elected President"}, {"date": "2021-07-25", "event": "Declared Exceptional Measures"}]},
    "p2":   {"id": "p2",   "name_fr": "Ahmed Hachani",     "role": "Head of Government", "history": [{"date": "2023-08-01", "event": "Appointed Head of Government"}]},
    "p3":   {"id": "p3",   "name_fr": "Kamel Feki",        "role": "Minister of Interior","history": [{"date": "2023-03-17", "event": "Appointed Minister"}]},
    "p31":  {"id": "p31",  "name_fr": "Moncef Sassi",      "role": "Central Director",   "history": [{"date": "2022-05-10", "event": "Appointed Central Director"}]},
    "p71":  {"id": "p71",  "name_fr": "Mohamed Ridha",     "role": "Director General",   "history": [{"date": "2021-12-01", "event": "Appointed Director General of Taxes"}]},
    "p141": {"id": "p141", "name_fr": "Hedi Slim",         "role": "Regional Director",  "history": [{"date": "2020-03-15", "event": "Appointed Regional Director of Education (Nabeul)"}]},
    "p131": {"id": "p131", "name_fr": "Karem Ben Ismail",  "role": "Director General",   "history": [{"date": "2022-09-20", "event": "Appointed DG of ANC"}]},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_has_data(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM institutions LIMIT 1")
        return cur.fetchone() is not None


def _person_history(conn, person_id: str) -> list:
    """Return chronological role history for a person from person_roles."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT pr.role_fr, i.name_fr AS institution, pr.valid_from, pr.valid_to, pr.action
            FROM   person_roles pr
            JOIN   institutions i ON i.id = pr.institution_id
            WHERE  pr.person_id = %s
            ORDER  BY pr.valid_from ASC
            """,
            (person_id,),
        )
        rows = cur.fetchall()
    return [
        {
            "date":  str(r["valid_from"]) if r["valid_from"] else None,
            "event": f"{r['action'] or 'Nommé'} — {r['role_fr']} ({r['institution']})",
        }
        for r in rows
    ]

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/snapshot")
def read_snapshot(date: str = Query(...)):
    """Full org chart at a specific date — live DB, mock fallback if empty."""
    try:
        conn = get_conn()
        if _db_has_data(conn):
            result = get_org_snapshot(conn, date)
            conn.close()
            return result
        conn.close()
    except Exception as e:
        logger.warning(f"DB unavailable, serving mock data: {e}")

    return {"institutions": MOCK_INSTITUTIONS}


@app.get("/api/search")
def search(q: str):
    """Search institutions and persons — live DB, mock fallback if empty."""
    results = []
    try:
        conn = get_conn()
        if _db_has_data(conn):
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                pattern = f"%{q}%"
                cur.execute(
                    """
                    SELECT id, name_fr, 'institution' AS type FROM institutions
                    WHERE name_fr ILIKE %s OR name_ar ILIKE %s
                    UNION ALL
                    SELECT id::text, name_fr, 'person' AS type FROM persons
                    WHERE name_fr ILIKE %s OR name_ar ILIKE %s
                    LIMIT 20
                    """,
                    (pattern, pattern, pattern, pattern),
                )
                results = [dict(r) for r in cur.fetchall()]
            conn.close()
            return {"results": results}
        conn.close()
    except Exception as e:
        logger.warning(f"DB unavailable, searching mock data: {e}")

    q_low = q.lower()
    for inst in MOCK_INSTITUTIONS:
        if q_low in inst["name_fr"].lower():
            results.append({"id": inst["id"], "name": inst["name_fr"], "type": "institution"})
        if inst["person"] and q_low in inst["person"]["name_fr"].lower():
            results.append({"id": inst["id"], "name": inst["person"]["name_fr"], "type": "person", "inst_id": inst["id"]})
    return {"results": results}


@app.get("/api/institutions/{id}")
def read_institution(id: str):
    try:
        conn = get_conn()
        if _db_has_data(conn):
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM institutions WHERE id = %s", (id,))
                row = cur.fetchone()
            conn.close()
            if not row:
                raise HTTPException(status_code=404, detail="Institution not found")
            return dict(row)
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"DB unavailable: {e}")

    inst = next((i for i in MOCK_INSTITUTIONS if i["id"] == id), None)
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return inst


@app.get("/api/persons/{id}")
def read_person(id: str):
    try:
        conn = get_conn()
        if _db_has_data(conn):
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM persons WHERE id = %s", (id,))
                row = cur.fetchone()
            if not row:
                conn.close()
                raise HTTPException(status_code=404, detail="Person not found")
            person = dict(row)
            person["history"] = _person_history(conn, id)
            conn.close()
            return person
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"DB unavailable: {e}")

    person = MOCK_PERSONS.get(id)
    if not person:
        inst = next((i for i in MOCK_INSTITUTIONS if i["person"] and i["person"]["id"] == id), None)
        if inst:
            return {"id": id, "name_fr": inst["person"]["name_fr"], "role": "Incumbent", "history": []}
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@app.get("/")
def health_check():
    return {"status": "ok"}
