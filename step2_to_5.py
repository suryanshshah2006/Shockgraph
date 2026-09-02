import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models import Company, Relationship, ScenarioImpact, ShockResult
from app.services.company_resolution import resolve_or_create_company

def run_dry():
    with Session(engine) as session:
        print("\n--- STEP 2: Delete TAIWAN and TAIWAN-SIL ---")
        for i in ['TAIWAN', 'TAIWAN-SIL']:
            rels = session.exec(select(Relationship).where((Relationship.supplier_id == i) | (Relationship.customer_id == i))).all()
            imps = session.exec(select(ScenarioImpact).where(ScenarioImpact.company_id == i)).all()
            shks = session.exec(select(ShockResult).where(ShockResult.company_id == i)).all()
            
            print(f"{i} References found:")
            print(f"  Relationships: {[(r.supplier_id, r.customer_id) for r in rels]}")
            print(f"  ScenarioImpacts: {[(r.scenario_id, r.company_id) for r in imps]}")
            print(f"  ShockResults: {[(r.scenario_id, r.company_id) for r in shks]}")
            
            # Delete references
            for r in rels + imps + shks:
                session.delete(r)
            c = session.get(Company, i)
            if c:
                session.delete(c)
            print(f"Deleted {i} and its references.")

        print("\n--- STEP 3: Manual Migration for TATA-MOTORS to TATAMOTORS.NS ---")
        tata_stub = session.get(Company, "TATA-MOTORS")
        if tata_stub:
            # We already have TATAMOTORS.NS?
            target = session.get(Company, "TATAMOTORS.NS")
            if target:
                print(f"Migrating TATA-MOTORS to TATAMOTORS.NS...")
                # Run standard resolution which handles duplicates
                tata_stub.ticker = "TATAMOTORS.NS"
                session.add(tata_stub)
                session.flush()
                # Use resolve_or_create_company
                resolve_or_create_company(session, query=tata_stub.name, ticker_hint="TATAMOTORS.NS", populate_relationships=False)
                print("TATA-MOTORS migrated.")
            else:
                print("TATAMOTORS.NS not found in DB?!")

        print("\n--- STEP 4: Update tickers and re-run resolution ---")
        updates = {
            "ASML-HOLDI": "ASML",
            "TOKYO-ELEC": "8035.T",
            "APPLIED-MA": "AMAT",
            "LAM-RESEAR": "LRCX",
            "SHIN-ETSU-": "4063.T",
            "APPLE-INC": "AAPL",
            "QUALCOMM-T": "QCOM",
            "QUALCOMM": "QCOM",
            "NVIDIA-COR": "NVDA",
            "NVIDIA": "NVDA",
            "ADVANCED-M": "AMD",
            "MEDIATEK-I": "2454.TW",
            "MEDIATEK": "2454.TW",
            "TSMC": "TSM",
            "KLA-CORPOR": "KLAC"
        }
        for old_id, new_ticker in updates.items():
            comp = session.get(Company, old_id)
            if comp:
                print(f"Updating {old_id} ticker to {new_ticker}")
                comp.ticker = new_ticker
                session.add(comp)
                session.flush()
                # Run resolution
                resolve_or_create_company(session, query=comp.name, ticker_hint=new_ticker, populate_relationships=False)

        print("\n--- STEP 5: Re-running cleanup_stubs loop ---")
        stubs = session.exec(select(Company).where(
            (Company.id != Company.ticker) |
            (Company.ticker == None) |
            (Company.market_cap == None)
        )).all()
        print(f"Found {len(stubs)} potential stubs.")
        
        migrated = []
        skipped_no_ticker = []
        skipped_fetch_failed = []
        
        for company in stubs:
            old_id = company.id
            ticker_hint = company.ticker
            
            new_company = resolve_or_create_company(
                session, 
                query=company.name, 
                ticker_hint=ticker_hint, 
                populate_relationships=False
            )
            
            if new_company.id != old_id:
                migrated.append(f"{old_id} -> {new_company.id}")
            else:
                if not ticker_hint:
                    skipped_no_ticker.append(old_id)
                else:
                    skipped_fetch_failed.append(old_id)
        
        print("\n=== FINAL DRY RUN REPORT ===")
        print(f"\nMigrated ({len(migrated)}):")
        for m in migrated:
            print(f"  {m}")
            
        print(f"\nSkipped (No Ticker) ({len(skipped_no_ticker)}):")
        for s in skipped_no_ticker:
            print(f"  {s}")
            
        print(f"\nSkipped (Fetch Failed) ({len(skipped_fetch_failed)}):")
        for s in skipped_fetch_failed:
            print(f"  {s}")
            
        print("\nDRY RUN: Rollback executing.")

if __name__ == "__main__":
    run_dry()
