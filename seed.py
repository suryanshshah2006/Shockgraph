import time
from sqlmodel import Session
from app.database import engine
from app.services.company_resolution import find_or_fetch_company

seed_list = [
    "AAPL", "TSM", "ASML", "NVDA", "AMZN", "MSFT", 
    "RELIANCE.NS", "TCS.NS", "TATAMOTORS.NS", "INFY.NS",
    "HDFCBANK.NS", "MARUTI.NS", "BHEL.NS", "LT.NS",
    "INTC", "AMD", "QCOM", "AVGO", "TXN"
]

def run_seed():
    print(f"Starting seed preload for {len(seed_list)} companies...")
    with Session(engine) as session:
        for ticker in seed_list:
            print(f"Resolving: {ticker}")
            try:
                company = find_or_fetch_company(session, ticker)
                print(f"Successfully processed {company.name} ({company.id})")
            except Exception as e:
                print(f"Failed to process {ticker}: {e}")
            time.sleep(1)
    print("Seed preload completed!")

if __name__ == "__main__":
    run_seed()