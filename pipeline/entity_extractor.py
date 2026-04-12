import os
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import ollama
from pydantic import BaseModel, Field, validator

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
EXTRACTED_DIR = DATA_DIR / "extracted"

# Pydantic Models for Schema Validation
class Person(BaseModel):
    name_fr: str
    name_ar: Optional[str] = None
    role_fr: str
    role_ar: Optional[str] = None
    institution_fr: str
    institution_ar: Optional[str] = None
    action: str = Field(..., pattern="^(appointed|removed|promoted|transferred)$")
    signed_by: Optional[str] = None

class Institution(BaseModel):
    name_fr: str
    name_ar: Optional[str] = None
    action: str = Field(..., pattern="^(created|dissolved|renamed|restructured|merged)$")
    parent_institution: Optional[str] = None
    new_name: Optional[str] = None

class Decree(BaseModel):
    decree_number: Optional[str] = None
    date_published: Optional[str] = None
    date_effective: Optional[str] = None
    decree_type: str = Field(..., pattern="^(nomination|revocation|restructuring|creation|dissolution|budget|other)$")
    persons: List[Person] = []
    institutions: List[Institution] = []
    confidence: float
    notes: Optional[str] = None

class JORTExtraction(BaseModel):
    decrees: List[Decree]

class EntityExtractor:
    def __init__(self, model: str = "llama3"):
        self.model = model
        self.system_prompt = """
You are an expert in Tunisian administrative law. Extract structured data from this JORT (Journal Officiel) page.
Return ONLY valid JSON, no markdown, no explanation.

Schema:
{
  "decrees": [{
    "decree_number": string | null,
    "date_published": "YYYY-MM-DD" | null,
    "date_effective": "YYYY-MM-DD" | null,
    "decree_type": "nomination" | "revocation" | "restructuring" | "creation" | "dissolution" | "budget" | "other",
    "persons": [{
      "name_fr": string,
      "name_ar": string | null,
      "role_fr": string,
      "role_ar": string | null,
      "institution_fr": string,
      "institution_ar": string | null,
      "action": "appointed" | "removed" | "promoted" | "transferred",
      "signed_by": string | null
    }],
    "institutions": [{
      "name_fr": string,
      "name_ar": string | null,
      "action": "created" | "dissolved" | "renamed" | "restructured" | "merged",
      "parent_institution": string | null,
      "new_name": string | null
    }],
    "confidence": 0.0-1.0,
    "notes": string | null
  }]
}
"""

    def extract_from_text(self, text: str) -> Optional[dict]:
        """Call Ollama to extract entities from text."""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self.system_prompt},
                    {'role': 'user', 'content': text},
                ],
                format='json'
            )
            content = response['message']['content']
            data = json.loads(content)
            
            # Validate with Pydantic
            validated_data = JORTExtraction(**data)
            return validated_data.dict()
            
        except Exception as e:
            logger.error(f"Ollama extraction failed: {e}")
            return None

    def process_all(self):
        """Iterate over extracted text files and run entity extraction."""
        if not EXTRACTED_DIR.exists():
            logger.error(f"Extracted directory {EXTRACTED_DIR} does not exist.")
            return

        for year_dir in EXTRACTED_DIR.iterdir():
            if not year_dir.is_dir(): continue
            
            for file in year_dir.glob("*.txt"):
                issue_num = file.stem
                if issue_num.endswith("_entities"): continue
                
                output_file = year_dir / f"{issue_num}_entities.json"
                if output_file.exists():
                    logger.info(f"Skipping {file} (entities already extracted)")
                    continue
                
                logger.info(f"Extracting entities from {file}")
                
                # Read content (skipping metadata header)
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    text_content = content.split("================\n\n")[-1]
                
                entities = self.extract_from_text(text_content)
                
                if entities:
                    # Filter for low confidence
                    for decree in entities['decrees']:
                        if decree['confidence'] < 0.7:
                            decree['needs_review'] = True
                        else:
                            decree['needs_review'] = False
                            
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(entities, f, indent=4, ensure_ascii=False)
                    logger.info(f"Saved entities to {output_file}")
                else:
                    logger.warning(f"Failed to extract entities for {file}")

def main():
    # Note: User must have Ollama running and the model pulled
    # pip install ollama
    # ollama pull llama3
    extractor = EntityExtractor(model="llama3")
    extractor.process_all()

if __name__ == "__main__":
    main()
