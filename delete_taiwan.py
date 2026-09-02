import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models import Company, Relationship, ScenarioImpact, ShockResult

def run_deletion():
    with Session(engine) as session:
        for i in ['TAIWAN', 'TAIWAN-SIL']:
            rels = session.exec(select(Relationship).where((Relationship.supplier_id == i) | (Relationship.customer_id == i))).all()
            imps = session.exec(select(ScenarioImpact).where(ScenarioImpact.company_id == i)).all()
            shks = session.exec(select(ShockResult).where(ShockResult.company_id == i)).all()
            
            for r in rels + imps + shks:
                session.delete(r)
            c = session.get(Company, i)
            if c:
                session.delete(c)
            print(f"Deleted {i} and {len(rels)} rels, {len(imps)} impacts, {len(shks)} shocks.")
        
        session.commit()
        print("Commit successful.")

if __name__ == "__main__":
    run_deletion()
