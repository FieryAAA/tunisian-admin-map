# Marsad Al-Idara — CLAUDE.md

Project context for AI assistant sessions. Read this before doing anything.

---

## Project Summary

**Marsad Al-Idara** — An enterprise-grade "système d'aide à la décision" that:
1. Scrapes all JORT (Journal Officiel de la République Tunisienne) issues since 1956
2. Runs OCR + Ollama LLM (NER) to extract nominations, revocations, institutional changes
3. Stores everything in a temporal PostgreSQL schema
4. Exposes a FastAPI REST API + React/D3.js frontend with a scrubbable timeline

Academic context: university project in Business Computing (Informatique de Gestion). Concepts: ETL pipeline, SCD-2 temporal model, DFD, BI/Power BI, public sector governance.

---

## Stack

| Layer | Tech |
|---|---|
| Database | PostgreSQL 16 + pgvector (Docker) |
| LLM / NER | Ollama (local, port 11434) |
| API | FastAPI + psycopg2-binary (port 8000) |
| Frontend | React + D3.js + dagre (Vite, port 3000) |
| Pipeline | Python 3.11: requests, BeautifulSoup, pytesseract, pdf2image, ollama |

---

## Running the App

```bash
# Start everything
docker compose up --build

# Frontend → http://localhost:3000
# API + Swagger → http://localhost:8000/docs
# DB → localhost:5432 (db: marsad, user: postgres, pass: password)
```

If DB volume is stale: `docker compose down -v && docker compose up --build`

Run the ETL pipeline (needs Tunisian IP for scraping):
```bash
docker compose --profile pipeline run --rm pipeline python scraper.py --from-year 2010 --to-year 2024
docker compose --profile pipeline run --rm pipeline python extractor.py
docker compose --profile pipeline run --rm pipeline python entity_extractor.py
docker compose --profile pipeline run --rm pipeline python resolver.py
```

---

## JORT Scraper — Full Reverse-Engineered URL Structure

**CRITICAL: iort.gov.tn is only reachable from Tunisian IPs.**

The site is a WinDev 12 WebApp. All navigation is session-based (stateful POST).
There are **6505 JORT issues** since 1956, containing 205,271 documents.

### Session Flow (fully reverse-engineered)

```
Step 1 — Establish session
  GET http://www.iort.gov.tn/WD120AWP/WD120Awp.exe/CONNECT/SITEIORT
  → Response has a <form> whose action contains the session CTX token:
    /WD120AWP/WD120Awp.exe/CTX_XXXX-N-YYYYYYY/Principal/SYNC_NNNN

Step 2 — Navigate to Arabic interface
  POST <form_action>
  WD_BUTTON_CLICK_=M21, WD_ACTION_=(empty)

Step 3 — Open search page (RechercheJORT)
  POST <new_action>
  WD_BUTTON_CLICK_=A8, WD_ACTION_=(empty)
  (include A12=1, A12_DEB=1, _A12_OCC=1 from previous form)

Step 4 — Search by year (A11 is the year dropdown)
  POST <new_action>
  WD_BUTTON_CLICK_=A24   ← this is the SEARCH button
  A11=<year_value>        ← year dropdown (see mapping below)
  A13=<issue_number>      ← specific issue number, or blank for all
  A4=<DD/MM/YYYY>         ← start date (optional)
  M9=<DD/MM/YYYY>         ← end date (optional)
  A7=1, A7_DEB=1, _A7_OCC=5   ← result list state
  A3=-1, A3_DEB=1, _A3_OCC=0  ← search criteria state
  WD_ACTION_=(empty)

Step 5 — Results appear in A7 list (5 per page)
  Each result row has two actions:
    _PAGE_.A7.value=N; _JSL(_PAGE_,'A14','_self','','')  → view issue
    _PAGE_.A7.value=N; _JSL(_PAGE_,'A30','_self','','')  → DOWNLOAD PDF ←

Step 6 — Download PDF for row N
  POST <current_action>
  WD_BUTTON_CLICK_=A30
  A7=<N>         ← row number (1-5)
  WD_ACTION_=(empty)
  → Returns application/pdf directly

Step 7 — Pagination (next page of results)
  GET <ctx_url>?WD_ACTION_=SCROLLTABLE&ZR=<page_number>
  Pages are numbered 2, 3, 4... with ">" for next
```

### A11 Year Dropdown Mapping

The `A11` SELECT has values 1–73. Mapping:
- `value='1'`  → (blank/all years)
- `value='2'`  → 2026
- `value='3'`  → 2025
- `value='4'`  → 2024
- `value='N'`  → 2028 - N  (formula: year = 2028 - value)
- `value='72'` → 1956
- `value='73'` → (blank)

**Formula: A11_value = 2028 - year** (e.g., 2020 → value '8')

### Key Button IDs

| Button | Meaning |
|---|---|
| M21 | Arabic interface |
| M32 | French interface |
| M33 | English interface |
| A8 | Open search page (RechercheJORT) |
| A24 | Execute search |
| A9 | Full-text search |
| A31 | Reset/clear form |
| A14 | View selected issue (A7.value=N) |
| A30 | **Download PDF** (A7.value=N) |
| A5 | Expand recent issues list (38 items) |
| A6 | Download PDF from recent list (A12.value=N) |

### Scraper Implementation Status

`pipeline/scraper.py` currently uses:
- Sequential probe (issues 1–160 per year)
- Tries legislation.tn HTML first, iort.gov.tn PDF fallback
- **NOT YET UPDATED** to use the RechercheJORT session mechanism above

**Next task: rewrite `pipeline/scraper.py`** to use the session flow above:
1. GET session → POST M21 → POST A8 → POST A24 with A11=year_value
2. For each result page: POST A30 with A7=row to download PDF
3. Paginate via SCROLLTABLE GET links
4. Store PDFs to `data/raw/{year}/{issue_num}/document.pdf`

---

## Database Schema (already implemented)

`backend/db/schema.sql` — temporal SCD-2 model:
- `persons` — public officials
- `institutions` — ministries, agencies, courts
- `decrees` — JORT source documents (+ pgvector embeddings)
- `person_roles` — **key table**: person ↔ institution with `valid_from`/`valid_to`
- `institution_hierarchy` — org chart with temporal validity
- `institution_events` — created/dissolved/renamed events

---

## API Endpoints

`backend/api/main.py` — wired to PostgreSQL, falls back to mock data if DB empty:
- `GET /api/snapshot?date=YYYY-MM-DD` — org chart at a date
- `GET /api/persons/{id}` — person + career history
- `GET /api/institutions/{id}` — institution detail
- `GET /api/search?q=...` — unified search

---

## Known Bugs Fixed (do not reintroduce)

1. `Dockerfile.db`: was `apache/age:latest` + `postgresql-18-pgvector` (version mismatch). Fixed → `pgvector/pgvector:pg16`
2. `pipeline/requirements.txt`: missing `pdf2image`. Fixed → added.
3. `backend/api/main.py`: was pure mock data. Fixed → wired to PostgreSQL.
4. `frontend/src/App.css`: missing `.loading-overlay`. Fixed → added.
5. `frontend/Dockerfile`: was `node:18-slim` (Vite needs Node 20+). Fixed → `node:20-slim`
6. `pipeline/scraper.py` line 166: `args.to-year` (Python subtraction bug). Fixed → `args.to_year`
7. `docker-compose.yml`: missing `api`, `frontend`, `pipeline` services. Fixed → added all.
8. `postgres_data` volume: was mounted at `/var/lib/postgresql` (wrong). Fixed → `/var/lib/postgresql/data`

---

## File Map

```
tunisian-admin-map/
├── backend/
│   ├── api/main.py          ← FastAPI, DB-wired, mock fallback
│   ├── db/
│   │   ├── schema.sql       ← full temporal schema + pgvector
│   │   ├── queries.py       ← get_org_snapshot() SQL query
│   │   └── loader.py        ← loads _entities.json → PostgreSQL
│   ├── Dockerfile.api
│   └── requirements.txt     ← fastapi, uvicorn, psycopg2-binary, etc.
├── pipeline/
│   ├── scraper.py           ← JORT downloader (needs session rewrite)
│   ├── extractor.py         ← OCR: OpenDataLoader → Tesseract fallback
│   ├── entity_extractor.py  ← Ollama LLM NER → _entities.json
│   ├── resolver.py          ← fuzzy name deduplication → stable UUIDs
│   ├── Dockerfile           ← includes tesseract-ocr-ara + fra
│   └── requirements.txt     ← requests, bs4, pytesseract, pdf2image, ollama
├── frontend/
│   ├── src/
│   │   ├── App.jsx          ← main layout, date scrubber state
│   │   ├── App.css          ← design system (CSS vars, dark mode)
│   │   ├── index.css        ← global reset + Inter font
│   │   └── components/
│   │       ├── OrgChart.jsx      ← D3.js + dagre hierarchical graph
│   │       ├── TimelineChart.jsx ← D3.js scrubbable timeline (1956→now)
│   │       └── ProfileDrawer.jsx ← sidebar: person/institution detail
│   ├── Dockerfile           ← node:20-slim
│   └── vite.config.js       ← host 0.0.0.0, port 3000
├── data/
│   ├── raw/                 ← downloaded PDFs/HTML (gitignored)
│   ├── extracted/           ← OCR text output (gitignored)
│   ├── resolved/            ← deduped entity registries (gitignored)
│   └── seeds/
│       └── known_ministers.json  ← pre-seeded minister names
├── docker-compose.yml       ← db, ollama, api, frontend, pipeline(profile)
└── Makefile                 ← setup / scrape / process / load / dev targets
```

---

## Next Steps (in priority order)

1. **Rewrite `pipeline/scraper.py`** using the WinDev session mechanism above
2. **Seed the DB** from `data/seeds/known_ministers.json` so UI shows real data
3. **Connect `entity_extractor.py` to Ollama** (pull `mistral` or `llama3` model)
4. **Add BI views** to PostgreSQL for Power BI dashboards
5. **Add `pipeline_runs` table** for ETL observability (PENDING→EXTRACTED→LOADED→FAILED)
