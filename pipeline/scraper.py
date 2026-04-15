"""
JORT Scraper for Marsad Al-Idara
---------------------------------
Downloads JORT (Journal Officiel de la République Tunisienne) issues
from iort.gov.tn and legislation.tn.

NOTE: iort.gov.tn is only reachable from Tunisian IP addresses.
      Run this script from inside Tunisia or over a Tunisian VPN.

Usage:
    python scraper.py --from-year 2010 --to-year 2024
    python scraper.py --from-year 1956 --to-year 2000   # scanned PDFs
"""

import os
import re
import time
import json
import random
import logging
import argparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
RAW_DIR      = DATA_DIR / "raw"
STATE_FILE   = DATA_DIR / "scrape_state.json"

# ── URL patterns ──────────────────────────────────────────────────────────────
# iort.gov.tn  → scanned PDFs, all years (primary archive)
IORT_BASE      = "http://www.iort.gov.tn/WD120AWP/WD120Awp.exe"
IORT_SITE      = f"{IORT_BASE}/CONNECT/SITEIORT"
IORT_YEAR_URL  = f"{IORT_BASE}/CTX/ListJORT?ANNEE={{year}}"          # index for a year
IORT_PDF_URL   = f"{IORT_BASE}/CTX/JORT/{{year}}/{{year}}{{issue:03d}}.pdf"  # direct PDF

# legislation.tn → digital HTML, post-2000 (faster/lighter)
LEGIS_BASE     = "http://www.legislation.tn"
LEGIS_HTML_URL = f"{LEGIS_BASE}/sites/default/files/jort/{{year}}/{{year}}{{issue:03d}}.html"

# ─────────────────────────────────────────────────────────────────────────────

class JortScraper:
    def __init__(self):
        self.session = self._build_session()
        self.state   = self._load_state()
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    # ── Session setup ──────────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://",  adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "Marsad-Al-Idara/1.0 (academic research; transparency.gov.tn)"
            ),
            "Accept-Language": "fr-TN,fr;q=0.9,ar;q=0.8",
        })
        return session

    # ── State persistence ──────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"downloaded_issues": {}}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def _is_downloaded(self, year: int, issue: int) -> bool:
        return str(issue) in self.state["downloaded_issues"].get(str(year), {})

    def _mark_downloaded(self, year: int, issue: int, path: Path):
        self.state["downloaded_issues"].setdefault(str(year), {})[str(issue)] = str(
            path.relative_to(PROJECT_ROOT)
        )
        self._save_state()

    # ── Issue discovery ────────────────────────────────────────────────────────

    def _discover_issues_from_index(self, year: int) -> list[int]:
        """
        Hit the iort.gov.tn year-index page and scrape issue numbers from it.
        Returns a sorted list of issue numbers found, or [] on failure.
        """
        url = IORT_YEAR_URL.format(year=year)
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            issues = set()
            # Look for links containing a year+issue pattern in href or text
            pattern = re.compile(rf"{year}(\d{{2,3}})", re.IGNORECASE)
            for tag in soup.find_all("a", href=True):
                m = pattern.search(tag["href"]) or pattern.search(tag.get_text())
                if m:
                    issues.add(int(m.group(1)))

            if issues:
                logger.info(f"  Index discovery: found {len(issues)} issues for {year}")
                return sorted(issues)
            else:
                logger.warning(f"  Index page returned no issue links for {year}: {url}")
                return []

        except Exception as e:
            logger.warning(f"  Index discovery failed for {year}: {e}")
            return []

    def _guess_issue_range(self, year: int) -> range:
        """
        Fallback: JORT publishes ~100-130 issues per year (bi-weekly + specials).
        We probe sequentially and stop after 10 consecutive 404s.
        """
        # Rough upper bounds per era
        if year < 1990:
            return range(1, 110)
        elif year < 2010:
            return range(1, 140)
        else:
            return range(1, 160)

    # ── Download logic ─────────────────────────────────────────────────────────

    def _download_pdf(self, year: int, issue: int, save_dir: Path) -> bool:
        url = IORT_PDF_URL.format(year=year, issue=issue)
        try:
            resp = self.session.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            # Verify it's actually a PDF
            if "application/pdf" not in resp.headers.get("Content-Type", ""):
                # Some servers serve 200 HTML error pages — check magic bytes
                first = next(resp.iter_content(4), b"")
                if first[:4] != b"%PDF":
                    logger.debug(f"  Not a PDF at {url}")
                    return False
                content = first + b"".join(resp.iter_content(8192))
            else:
                content = b"".join(resp.iter_content(8192))

            out = save_dir / "document.pdf"
            out.write_bytes(content)
            logger.info(f"  ✓ PDF  {year}/{issue:03d}  ({len(content)//1024} KB)")
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return False
            logger.error(f"  HTTP error for PDF {year}/{issue}: {e}")
            return False
        except Exception as e:
            logger.error(f"  Failed to download PDF {year}/{issue}: {e}")
            return False

    def _download_html(self, year: int, issue: int, save_dir: Path) -> bool:
        url = LEGIS_HTML_URL.format(year=year, issue=issue)
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            out = save_dir / "index.html"
            out.write_text(resp.text, encoding="utf-8")
            logger.info(f"  ✓ HTML {year}/{issue:03d}")
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return False
            logger.error(f"  HTTP error for HTML {year}/{issue}: {e}")
            return False
        except Exception as e:
            logger.error(f"  Failed to download HTML {year}/{issue}: {e}")
            return False

    def _download_issue(self, year: int, issue: int) -> bool:
        save_dir = RAW_DIR / str(year) / str(issue)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Strategy: try HTML first for post-2000 (lighter), then PDF
        success = False
        if year >= 2000:
            success = self._download_html(year, issue, save_dir)
        if not success:
            success = self._download_pdf(year, issue, save_dir)

        if success:
            self._mark_downloaded(year, issue, save_dir)
        return success

    # ── Year processing ────────────────────────────────────────────────────────

    def process_year(self, year: int):
        logger.info(f"── Year {year} ──────────────────────────────")

        # 1. Try index discovery first
        issue_list = self._discover_issues_from_index(year)

        # 2. If index failed, probe the issue range directly
        if not issue_list:
            logger.info(f"  Falling back to sequential probe for {year}")
            issue_list = list(self._guess_issue_range(year))

        consecutive_misses = 0
        for issue in issue_list:
            if self._is_downloaded(year, issue):
                logger.debug(f"  Skip {year}/{issue} (already downloaded)")
                consecutive_misses = 0
                continue

            success = self._download_issue(year, issue)

            if success:
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                # If probing sequentially, stop after 10 misses in a row
                if not self._discover_issues_from_index.__doc__ and consecutive_misses >= 10:
                    logger.info(f"  10 consecutive misses — stopping probe for {year}")
                    break

            # Respectful rate limiting: 1–2 s between requests
            time.sleep(1.0 + random.uniform(0, 0.75))

    # ── Entry point ────────────────────────────────────────────────────────────

    def run(self, from_year: int, to_year: int):
        logger.info(f"Starting JORT scrape: {from_year} → {to_year}")
        for year in range(from_year, to_year + 1):
            self.process_year(year)
        logger.info("Scrape complete.")


# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="JORT downloader for Marsad Al-Idara")
    parser.add_argument("--from-year", type=int, required=True, help="First year to scrape")
    parser.add_argument("--to-year",   type=int, required=True, help="Last year to scrape (inclusive)")
    args = parser.parse_args()

    if args.from_year > args.to_year:          # ← was: args.to-year (bug fixed)
        parser.error("--from-year must be ≤ --to-year")

    JortScraper().run(args.from_year, args.to_year)


if __name__ == "__main__":
    main()
