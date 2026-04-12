import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Any

from rapidfuzz import fuzz, process

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
RESOLVED_DIR = DATA_DIR / "resolved"

class EntityResolver:
    def __init__(self, threshold: int = 88):
        self.threshold = threshold
        self.persons: Dict[str, Any] = {} # canonical_name -> {id, variants, ...}
        self.institutions: Dict[str, Any] = {}
        
        RESOLVED_DIR.mkdir(parents=True, exist_ok=True)

    def _get_or_create_id(self, name_fr: str, entity_type: str) -> str:
        """Resolve an entity name to a stable ID using fuzzy matching."""
        store = self.persons if entity_type == "person" else self.institutions
        
        if not store:
            new_id = str(uuid.uuid4())
            store[name_fr] = {"id": new_id, "variants": [name_fr]}
            return new_id
            
        # Fuzzy match against existing canonical names
        match = process.extractOne(name_fr, store.keys(), scorer=fuzz.WRatio)
        
        if match and match[1] >= self.threshold:
            canonical_name = match[0]
            if name_fr not in store[canonical_name]["variants"]:
                store[canonical_name]["variants"].append(name_fr)
            return store[canonical_name]["id"]
        else:
            # New entity
            new_id = str(uuid.uuid4())
            store[name_fr] = {"id": new_id, "variants": [name_fr]}
            return new_id

    def load_entities(self):
        """Walk through extracted entities and resolve them."""
        if not EXTRACTED_DIR.exists():
            logger.error(f"Extracted directory {EXTRACTED_DIR} does not exist.")
            return

        for entities_file in EXTRACTED_DIR.rglob("*_entities.json"):
            logger.info(f"Resolving entities from {entities_file}")
            with open(entities_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for decree in data.get('decrees', []):
                for p in decree.get('persons', []):
                    p['person_id'] = self._get_or_create_id(p['name_fr'], "person")
                    
                for inst in decree.get('institutions', []):
                    inst['institution_id'] = self._get_or_create_id(inst['name_fr'], "institution")
            
            # Save updated file with IDs (optional, or just build the central registry)
            # with open(entities_file, 'w', encoding='utf-8') as f:
            #     json.dump(data, f, indent=4, ensure_ascii=False)

    def save_resolved(self):
        """Save the resolved entity registries."""
        persons_out = RESOLVED_DIR / "persons.json"
        inst_out = RESOLVED_DIR / "institutions.json"
        
        # Format for output
        plist = [{"id": v["id"], "name_fr": k, "variants": v["variants"]} for k, v in self.persons.items()]
        ilist = [{"id": v["id"], "name_fr": k, "variants": v["variants"]} for k, v in self.institutions.items()]
        
        with open(persons_out, 'w', encoding='utf-8') as f:
            json.dump(plist, f, indent=4, ensure_ascii=False)
            
        with open(inst_out, 'w', encoding='utf-8') as f:
            json.dump(ilist, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Saved {len(plist)} persons to {persons_out}")
        logger.info(f"Saved {len(ilist)} institutions to {inst_out}")

def main():
    resolver = EntityResolver(threshold=88)
    resolver.load_entities()
    resolver.save_resolved()

if __name__ == "__main__":
    main()
