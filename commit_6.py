import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models import Company
from app.services.company_resolution import resolve_or_create_company

def commit_6():
    ids_to_migrate = [
        "APPLIED-MA-2",
        "LAM-RESEAR-2",
        "BHARAT-FORGE",
        "ASAHI-INDIA-",
        "MAHINDRA-MAH",
        "APOLLO-TYRES"
    ]
    with Session(engine) as session:
        for old_id in ids_to_migrate:
            company = session.get(Company, old_id)
            if not company:
                print(f"Not found: {old_id}")
                continue
            
            new_company = resolve_or_create_company(
                session, 
                query=company.name, 
                ticker_hint=company.ticker, 
                populate_relationships=False
            )
            print(f"Migrated {old_id} -> {new_company.id}")
        session.commit()
        print("Committed the 6 clean migrations.")

if __name__ == "__main__":
    commit_6()
