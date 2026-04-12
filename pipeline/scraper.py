import os
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STATE_FILE = DATA_DIR / "scrape_state.json"

class JortScraper:
    def __init__(self):
        self.session = self._setup_session()
        self.state = self._load_state()
        
        # Ensure directories exist
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        
    def _setup_session(self):
        """Configure requests session with retries and backoff."""
        session = requests.Session()
        # Exponential backoff: {backoff factor} * (2 ** ({number of total retries} - 1))
        retry = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=1,
            status_forcelist=(500, 502, 503, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Marsad Al-Idara Data Pipeline/1.0'
        })
        return session

    def _load_state(self):
        """Load the scrape state to track what's been downloaded."""
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"downloaded_issues": {}}

    def _save_state(self):
        """Save the current scrape state."""
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=4)

    def _is_downloaded(self, year, issue_num):
        """Check if an issue was already downloaded."""
        y_str = str(year)
        if y_str in self.state["downloaded_issues"]:
            return str(issue_num) in self.state["downloaded_issues"][y_str]
        return False

    def _mark_downloaded(self, year, issue_num, file_path):
        """Mark an issue as downloaded in the state file."""
        y_str = str(year)
        if y_str not in self.state["downloaded_issues"]:
            self.state["downloaded_issues"][y_str] = {}
        self.state["downloaded_issues"][y_str][str(issue_num)] = str(file_path)
        self._save_state()

    def process_year(self, year):
        """Process all issues for a given year."""
        logger.info(f"Starting scrape for year: {year}")
        
        # The actual number of issues per year varies. Typically ~100-150 issues.
        # This is a mocked generator. In reality, you'd scrape an index page for the year.
        # For demonstration and structure matching, we simulate finding 5 issues per year.
        issues_to_scrape = range(1, 6) 
        
        for issue_num in issues_to_scrape:
            if self._is_downloaded(year, issue_num):
                logger.info(f"Skipping year {year} issue {issue_num} (already downloaded)")
                continue
                
            self.download_issue(year, issue_num)
            
            # Respect rate limit of 1 request/second + variance
            time.sleep(1 + random.uniform(0, 0.5))

    def download_issue(self, year, issue_num):
        """Download a specific JORT issue."""
        save_dir = RAW_DIR / str(year) / str(issue_num)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Post-2000 from legislation.tn (HTML), Pre-2000 from iort.gov.tn (PDF)
        if year >= 2000:
            self._download_html(year, issue_num, save_dir)
        else:
            self._download_pdf(year, issue_num, save_dir)

    def _download_html(self, year, issue_num, save_dir):
        """Fetch HTML from legislation.tn."""
        # Simulated endpoint. You will need to inspect legislation.tn for the exact URL structure
        url = f"http://www.legislation.tn/sites/default/files/jort/{year}/{year}{issue_num:03d}.html"
        logger.info(f"Fetching HTML for {year} issue {issue_num}: {url}")
        
        try:
            # We use a mock response to test the pipeline without spamming real servers
            # In production, uncomment the request:
            # response = self.session.get(url, timeout=10)
            # response.raise_for_status()
            # html_content = response.text
            
            html_content = f"<html><body><h1>JORT Issue N {issue_num} of Year {year}</h1><p>Test HTML structure</p></body></html>"
            
            file_path = save_dir / "index.html"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self._mark_downloaded(year, issue_num, file_path.relative_to(PROJECT_ROOT))
            
        except Exception as e:
            logger.error(f"Failed to download HTML for {year} issue {issue_num}: {e}")

    def _download_pdf(self, year, issue_num, save_dir):
        """Fetch PDF from iort.gov.tn."""
        # Simulated endpoint.
        url = f"http://www.iort.gov.tn/WD120AWP/WD120Awp.exe/CTX/JORT/{year}/{year}{issue_num:03d}.pdf"
        logger.info(f"Fetching PDF for {year} issue {issue_num}: {url}")
        
        try:
            # In production, you would stream to file:
            # response = self.session.get(url, stream=True, timeout=15)
            # response.raise_for_status()
            
            file_path = save_dir / "document.pdf"
            
            # Simulated binary file
            with open(file_path, 'wb') as f:
                f.write(b"%PDF-1.4 mock pdf data")
            
            self._mark_downloaded(year, issue_num, file_path.relative_to(PROJECT_ROOT))
            
        except Exception as e:
            logger.error(f"Failed to download PDF for {year} issue {issue_num}: {e}")


def main():
    parser = argparse.ArgumentParser(description="JORT Downloader for Marsad Al-Idara")
    parser.add_argument("--from-year", type=int, required=True, help="Start year of the scrape")
    parser.add_argument("--to-year", type=int, required=True, help="End year of the scrape")
    
    args = parser.parse_args()
    
    if args.from_year > args.to-year:
        logger.error("from-year must be less than or equal to to-year")
        return

    scraper = JortScraper()
    
    for year in range(args.from_year, args.to_year + 1):
        scraper.process_year(year)

if __name__ == "__main__":
    main()
