# Marsad Al-Idara (مرصد الإدارة)

An interactive map of Tunisian public administration built by scraping and parsing JORT (Journal Officiel de la République Tunisienne) archives.

## Architecture

```ascii
                                +-------------------+
                                |   JORT Sources    |
                                | (legislation.tn)  |
                                +---------+---------+
                                          |
                                          v
+------------------+         +------------+------------+
|  Data Pipeline   |         |    Scraper (Python)     |
| (pipeline/)      +-------->|    Extractor (OCR)      |
|                  |         |    Ollama (LLM)         |
+---------+--------+         +------------+------------+
          |                               |
          v                               v
+---------+--------+         +------------+------------+
|    PostgreSQL    |         |  Entity Resolution      |
| (Graph + Vector) | <-------+  Data Loader (Python)   |
+---------+--------+         +-------------------------+
          |
          v
+---------+--------+         +-------------------------+
|   FastAPI API    | <-------+  React + D3 Frontend    |
|   (backend/api)  |         |  (Interactive Map)      |
+------------------+         +-------------------------+
```

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Ollama (running locally on port 11434 with `llama3` model)

### Quick Start
```bash
# 1. Start all services (Postgres, API, Frontend, Ollama proxy)
make setup

# 2. Run the scraping pipeline (fetches ~5 years by default)
make scrape

# 3. Extract and resolve entities using local Ollama model
make process

# 4. Load processed data into the DB
make load

# 5. Start the Dev environment
make dev
```

### Accessing the services
- **Frontend UI**: http://localhost:3000
- **FastAPI Metadata**: http://localhost:8000/docs
- **Postgres Database**: port 5432 (user: postgres, pass: password)

## Features Implementation
- [x] **Temporal Graph**: Institutions and roles are tracked over time.
- [x] **OCR Fallback**: Automated detection of scanned PDFs with Tesseract.
- [x] **Modern UI**: D3.js powered timeline with regime/era highlighting and drag-scrubbing.
- [x] **Fuzzy Name Resolution**: Handling name variants in French and Arabic.
- [x] **Zero-Cost LLM**: Powered by Ollama instead of expensive APIs.
