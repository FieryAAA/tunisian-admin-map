import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def get_snapshot_query(date: str) -> str:
    """
    Returns the SQL query to fetch the full institutional hierarchy 
    and personnel on a specific date.
    
    The query joins institutions with hierarchy and person roles 
    filtered by the provided temporal date.
    """
    return f"""
    SELECT 
        i.id as institution_id,
        i.name_fr as institution_name_fr,
        i.name_ar as institution_name_ar,
        i.type as institution_type,
        p.id as person_id,
        p.name_fr as person_name_fr,
        p.name_ar as person_name_ar,
        pr.role_fr,
        pr.role_ar,
        ih.parent_id
    FROM institutions i
    LEFT JOIN institution_hierarchy ih 
        ON ih.child_id = i.id 
        AND ih.valid_from <= '{date}' 
        AND (ih.valid_to IS NULL OR ih.valid_to > '{date}')
    LEFT JOIN person_roles pr 
        ON pr.institution_id = i.id 
        AND pr.valid_from <= '{date}' 
        AND (pr.valid_to IS NULL OR pr.valid_to > '{date}')
    LEFT JOIN persons p 
        ON p.id = pr.person_id
    ORDER BY i.name_fr;
    """

def get_org_snapshot(conn, date: str) -> Dict[str, Any]:
    """
    Executes the snapshot query and formats the result as a nested dictionary
    representing the hierarchy and personnel.
    """
    query = get_snapshot_query(date)
    
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            
            # Simple transformation logic (can be expanded based on frontend needs)
            snapshot = {
                "date": date,
                "institutions": []
            }
            
            for row in rows:
                snapshot["institutions"].append({
                    "id": row[0],
                    "name_fr": row[1],
                    "name_ar": row[2],
                    "type": row[3],
                    "person": {
                        "id": row[4],
                        "name_fr": row[5],
                        "name_ar": row[6],
                        "role": row[7]
                    } if row[4] else None,
                    "parent_id": row[9]
                })
                
            return snapshot
    except Exception as e:
        logger.error(f"Failed to fetch snapshot for {date}: {e}")
        return {"error": str(e)}
