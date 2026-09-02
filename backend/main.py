from fastapi import FastAPI, Depends, Query
from sqlmodel import Session
from database import init_db, get_session
import models
import services

app = FastAPI(title="Supply Chain Graph API")

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/companies")
def list_companies(skip: int = 0, limit: int = 10, session: Session = Depends(get_session)):
    pass

@app.get("/companies/{id}")
def get_company(id: str, session: Session = Depends(get_session)):
    pass

@app.post("/companies/resolve")
def resolve_companies(session: Session = Depends(get_session)):
    pass

@app.get("/companies/{id}/graph")
def get_company_graph(id: str, depth: int = Query(2), session: Session = Depends(get_session)):
    pass

@app.post("/scenarios")
def create_scenario(session: Session = Depends(get_session)):
    pass

@app.get("/scenarios/{id}")
def get_scenario(id: str, session: Session = Depends(get_session)):
    pass

@app.post("/market-data/refresh")
def refresh_market_data(session: Session = Depends(get_session)):
    pass
