from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models import Company, Relationship
from app.services.company_resolution import resolve_or_create_company
from app.services.llm_service import LLMServiceError

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyResolveRequest(BaseModel):
    query: str


@router.get("")
def list_companies(
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    session: Session = Depends(get_session),
):
    return session.exec(select(Company).offset(skip).limit(limit)).all()


@router.get("/{company_id}")
def get_company(company_id: str, session: Session = Depends(get_session)):
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("/resolve")
def resolve_company(payload: CompanyResolveRequest, session: Session = Depends(get_session)):
    try:
        company = resolve_or_create_company(session, payload.query)
    except LLMServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    session.commit()
    session.refresh(company)
    return company


@router.get("/{company_id}/graph")
def get_company_graph(company_id: str, depth: int = 2, session: Session = Depends(get_session)):
    root = session.get(Company, company_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Company not found")

    visited_ids = {company_id}
    frontier = {company_id}
    edges: list[Relationship] = []
    seen_edge_ids = set()

    for _ in range(depth):
        if not frontier:
            break
        rels = session.exec(
            select(Relationship).where(
                Relationship.supplier_id.in_(frontier) | Relationship.customer_id.in_(frontier)
            )
        ).all()

        next_frontier = set()
        for rel in rels:
            if rel.id not in seen_edge_ids:
                seen_edge_ids.add(rel.id)
                edges.append(rel)
            for node_id in (rel.supplier_id, rel.customer_id):
                if node_id not in visited_ids:
                    visited_ids.add(node_id)
                    next_frontier.add(node_id)
        frontier = next_frontier

    nodes = session.exec(select(Company).where(Company.id.in_(visited_ids))).all()

    return {"nodes": nodes, "edges": edges}
