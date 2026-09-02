from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.post("/refresh")
def refresh_market_data(session: Session = Depends(get_session)):
    raise HTTPException(status_code=501, detail="Not implemented")
