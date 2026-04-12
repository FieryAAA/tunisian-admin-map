import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

import pdfplumber
from pdf2image import convert_from_path
import pytesseract
import arabic_reshaper
from bidi.algorithm import get_display

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
EXTRACTED_DIR = DATA_DIR / "extracted"

class JortExtractor:
    def __init__(self):
        EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    def _fix_arabic_text(self, text):
        """Fix RTL and character connection for Arabic text to work well with OCR."""
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except Exception as e:
            logger.warning(f"Error reshaping Arabic text: {e}")
            return text

    def _extract_text_pdfplumber(self, file_path):
        """Extract text directly using pdfplumber."""
        pages_content = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        pages_content.append(text)
                    else:
                        pages_content.append("")
        except Exception as e:
            logger.error(f"pdfplumber extraction failed for {file_path}: {e}")
            
        return pages_content

    def _extract_text_tesseract(self, file_path):
        """Extract text using OCR for scanned PDFs."""
        pages_content = []
        try:
            # Requires poppler-utils installed on system
            images = convert_from_path(file_path)
            for i, image in enumerate(images):
                # Using Arabic + French language packs, psm 6 (Assume a single uniform block of text)
                text = pytesseract.image_to_string(image, lang='ara+fra', config='--psm 6')
                pages_content.append(text)
        except Exception as e:
            logger.error(f"pytesseract extraction failed for {file_path}: {e}")
            
        return pages_content

    def process_file(self, file_path, year, issue_number):
        """Process a single raw file."""
        file_ext = file_path.suffix.lower()
        full_text = ""
        is_scan = False
        
        if file_ext == ".pdf":
            pages_text = self._extract_text_pdfplumber(file_path)
            
            # Check if likely a scan (< 50 chars per page on average)
            total_chars = sum(len(page) for page in pages_text)
            avg_chars = total_chars / max(1, len(pages_text))
            
            if avg_chars < 50:
                logger.info(f"{file_path} identified as scan. Falling back to OCR.")
                is_scan = True
                pages_text = self._extract_text_tesseract(file_path)
                
            full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
            
        elif file_ext == ".html" or file_ext == ".htm":
            # For modern HTML JORTs (post-2000)
            try:
                from bs4 import BeautifulSoup
                with open(file_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), "html.parser")
                    full_text = soup.get_text(separator="\n", strip=True)
            except Exception as e:
                logger.error(f"Failed to parse HTML {file_path}: {e}")
        else:
            logger.warning(f"Unsupported file format: {file_ext}")
            return False

        # Apply Arabic formatting correction globally
        full_text = self._fix_arabic_text(full_text)
        
        # Save output
        self._save_extracted(year, issue_number, full_text, file_ext, is_scan)
        return True

    def _save_extracted(self, year, issue_number, content, source_type, is_scan):
        """Save extracted text with metadata header."""
        save_dir = EXTRACTED_DIR / str(year)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        out_file = save_dir / f"{issue_number}.txt"
        
        metadata = {
            "year": year,
            "issue_number": issue_number,
            "source_type": source_type,
            "is_scan_ocr": is_scan,
            "extracted_at": datetime.now().isoformat()
        }
        
        header = f"=== METADATA ===\n{json.dumps(metadata, indent=2)}\n================\n\n"
        
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(header + content)
            
        logger.info(f"Saved extracted text to {out_file}")

    def run_all(self):
        """Iterate over all raw files and extract them."""
        # Find all raw directories
        if not RAW_DIR.exists():
            logger.error(f"Raw directory {RAW_DIR} does not exist.")
            return

        for year_dir in RAW_DIR.iterdir():
            if not year_dir.is_dir(): continue
            
            for issue_dir in year_dir.iterdir():
                if not issue_dir.is_dir(): continue
                
                year = year_dir.name
                issue_num = issue_dir.name
                
                # Already extracted?
                expected_out = EXTRACTED_DIR / year / f"{issue_num}.txt"
                if expected_out.exists():
                    logger.info(f"Skipping {year}/{issue_num} (already extracted)")
                    continue
                
                # Find the target file (.html or .pdf or .htm)
                target_file = None
                for f in issue_dir.iterdir():
                    if f.suffix.lower() in [".pdf", ".html", ".htm"]:
                        target_file = f
                        break
                        
                if target_file:
                    logger.info(f"Processing {target_file}")
                    self.process_file(target_file, year, issue_num)
                else:
                    logger.warning(f"No valid target file found in {issue_dir}")

def main():
    extractor = JortExtractor()
    logger.info("Starting batch extraction process...")
    extractor.run_all()
    logger.info("Batch extraction complete.")

if __name__ == "__main__":
    main()
