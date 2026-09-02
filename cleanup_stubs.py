import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models import Company
from app.services.company_resolution import resolve_or_create_company

def run_cleanup():
    with Session(engine) as session:
        stubs = session.exec(select(Company).where(
            (Company.id != Company.ticker) |
            (Company.ticker == None) |
            (Company.market_cap == None)
        )).all()
        print(f"Found {len(stubs)} potential stubs.", flush=True)
        
        migrated = []
        updated_in_place = []
        skipped_no_ticker = []
        skipped_fetch_failed = []
        
        for company in stubs:
            old_id = company.id
            ticker_hint = company.ticker
            
            print(f"Processing {old_id}...", flush=True)
            
            new_company = resolve_or_create_company(
                session, 
                query=company.name, 
                ticker_hint=ticker_hint, 
                populate_relationships=False
            )
            
            if new_company.id != old_id:
                migrated.append(f"{old_id} -> {new_company.id}")
            elif new_company.market_cap is not None:
                updated_in_place.append(f"{old_id} (ticker: {new_company.ticker})")
            else:
                if not ticker_hint:
                    skipped_no_ticker.append(old_id)
                else:
                    skipped_fetch_failed.append(old_id)
        
        print("\n=== CLEANUP REPORT ===", flush=True)
        print(f"\nMigrated ({len(migrated)}):", flush=True)
        for m in migrated:
            print(f"  {m}", flush=True)
            
        print(f"\nUpdated In-Place ({len(updated_in_place)}):", flush=True)
        for u in updated_in_place:
            print(f"  {u}", flush=True)
            
        print(f"\nSkipped (No Ticker) ({len(skipped_no_ticker)}):", flush=True)
        for s in skipped_no_ticker:
            print(f"  {s}", flush=True)
            
        print(f"\nSkipped (Fetch Failed) ({len(skipped_fetch_failed)}):", flush=True)
        for s in skipped_fetch_failed:
            print(f"  {s}", flush=True)
            
        session.commit()
        print("\nSUCCESS: Transaction was committed to the database.", flush=True)

if __name__ == "__main__":
    run_cleanup()
