import os
import json
import logging
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EXTRACTED_DIR = DATA_DIR / "extracted"

DB_CONFIG = {
    "dbname": "marsad",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5432
}

class JortLoader:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True

    def _upsert_person(self, person_data):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO persons (name_fr, name_ar, name_variants)
                VALUES (%s, %s, ARRAY[%s])
                ON CONFLICT (name_fr) DO UPDATE 
                SET name_ar = EXCLUDED.name_ar,
                    name_variants = array_distinct(persons.name_variants || EXCLUDED.name_variants)
                RETURNING id;
            """, (person_data['name_fr'], person_data['name_ar'], person_data['name_fr']))
            return cur.fetchone()[0]

    def _upsert_institution(self, inst_data):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO institutions (name_fr, name_ar, name_variants)
                VALUES (%s, %s, ARRAY[%s])
                ON CONFLICT (name_fr) DO UPDATE 
                SET name_ar = EXCLUDED.name_ar,
                    name_variants = array_distinct(institutions.name_variants || EXCLUDED.name_variants)
                RETURNING id;
            """, (inst_data['name_fr'], inst_data['name_ar'], inst_data['name_fr']))
            return cur.fetchone()[0]

    def load_entities(self):
        """Walk through extracted entities.json files and load into DB."""
        for entities_file in EXTRACTED_DIR.rglob("*_entities.json"):
            logger.info(f"Loading {entities_file}")
            with open(entities_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for decree_data in data.get('decrees', []):
                # 1. Insert Decree
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO decrees (decree_number, date_published, date_effective, decree_type, confidence)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (
                        decree_data.get('decree_number'),
                        decree_data.get('date_published'),
                        decree_data.get('date_effective'),
                        decree_data.get('decree_type'),
                        decree_data.get('confidence')
                    ))
                    decree_id = cur.fetchone()[0]

                # 2. Insert Persons & Roles
                for p in decree_data.get('persons', []):
                    # For demo/simplicity, we lookup by name_fr as a proxy for person_id
                    # In production, we'd use the resolver's stable person_id
                    person_id = self._upsert_person(p)
                    inst_id = self._upsert_institution({'name_fr': p['institution_fr'], 'name_ar': p['institution_ar']})
                    
                    with self.conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO person_roles (person_id, institution_id, role_fr, role_ar, valid_from, decree_id, action)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            person_id, inst_id, p['role_fr'], p['role_ar'], 
                            decree_data.get('date_effective') or decree_data.get('date_published'),
                            decree_id, p['action']
                        ))

                # 3. Insert Institutions & Hierarchy
                for inst in decree_data.get('institutions', []):
                    inst_id = self._upsert_institution(inst)
                    if inst.get('parent_institution'):
                        parent_id = self._upsert_institution({'name_fr': inst['parent_institution'], 'name_ar': None})
                        with self.conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO institution_hierarchy (child_id, parent_id, valid_from, decree_id)
                                VALUES (%s, %s, %s, %s)
                            """, (
                                inst_id, parent_id,
                                decree_data.get('date_effective') or decree_data.get('date_published'),
                                decree_id
                            ))

def main():
    # Note: This requires a helper function `array_distinct` in postgres or a slightly different SQL approach.
    # We'll stick to a simpler UPSERT for now.
    loader = JortLoader()
    loader.load_entities()

if __name__ == "__main__":
    main()
