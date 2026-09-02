from uuid import UUID
import networkx as nx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.database import get_session
from app.models import Company, Relationship, Scenario, ScenarioImpact, ShockResult
from app.services.company_resolution import find_or_fetch_company
from app.services.llm_service import LLMServiceError, extract_scenario_impacts
from app.services.propagation import propagate_with_depth
from app.limiter import limiter

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

def _build_graph(session: Session) -> nx.DiGraph:
    graph = nx.DiGraph()
    for rel in session.exec(select(Relationship)).all():
        graph.add_edge(
            rel.supplier_id,
            rel.customer_id,
            weight=rel.weight,
            relationship_type=rel.relationship_type,
            source_ref=rel.source_ref,
        )
    return graph


@router.post("")
@limiter.limit("10/minute")
def create_scenario(request: Request, payload: str, session: Session = Depends(get_session)):
    raw_text = payload.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="A scenario prompt is required")

    try:
        extraction = extract_scenario_impacts(raw_text)
    except LLMServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    scenario = Scenario(raw_text=raw_text, scenario_type=extraction.get("scenario_type", "chain_shock"))
    session.add(scenario)
    session.flush()

    direct_impacts: dict[str, float] = {}
    impacts_list = []
    
    for item in extraction.get("impacts", []):
        try:
            company = find_or_fetch_company(
                session, 
                query=item["company_query"], 
                ticker_hint=item.get("ticker")
            )
            if not company:
                continue

            impact = ScenarioImpact(
                scenario_id=scenario.id,
                company_id=company.id,
                direct_shock_pct=item["direct_shock_pct"],
                reasoning=item.get("reasoning", ""),
            )
            session.add(impact)
            impacts_list.append({
                "company_id": company.id,
                "name": company.name,
                "ticker": company.ticker,
                "direct_shock_pct": item["direct_shock_pct"],
                "reasoning": item.get("reasoning", "")
            })
            direct_impacts[company.id] = direct_impacts.get(company.id, 0.0) + item["direct_shock_pct"]
        except Exception as e:
            print(f"[-] Resolution error for {item.get('company_query')}: {e}")
            continue

    if not direct_impacts:
        return {
            "scenario_type": scenario.scenario_type,
            "impacts": [],
            "shock_results": [],
            "edges": []
        }

    graph = _build_graph(session)
    results, depths = propagate_with_depth(graph, direct_impacts)

    shock_results_list = []
    for company_id, total_impact_pct in results.items():
        company = session.get(Company, company_id)
        market_cap = company.market_cap if company else None
        dollar_impact = (
            (total_impact_pct / 100.0) * market_cap
            if market_cap is not None
            else None
        )
        shock_result = ShockResult(
            scenario_id=scenario.id,
            company_id=company_id,
            total_impact_pct=total_impact_pct,
            dollar_impact=dollar_impact,
            depth=depths.get(company_id, 0),
        )
        session.add(shock_result)
        shock_results_list.append({
            "company_id": company_id,
            "name": company.name if company else company_id,
            "ticker": company.ticker if company else company_id,
            "sector": company.sector if company else "N/A",
            "market_cap": market_cap,
            "total_impact_pct": total_impact_pct,
            "dollar_impact": dollar_impact,
            "depth": depths.get(company_id, 0),
            "is_epicenter": depths.get(company_id, 0) == 0,
        })

    session.commit()

    affected_ids = set(results.keys())
    edges_list = []
    for u, v, data in graph.edges(data=True):
        if u in affected_ids and v in affected_ids:
            edges_list.append({
                "from": u,
                "to": v,
                "weight": data.get("weight", 0.5),
                "relationship_type": data.get("relationship_type", "dependency"),
                "source_ref": data.get("source_ref", "")
            })

    return {
        "scenario_type": scenario.scenario_type,
        "impacts": impacts_list,
        "shock_results": shock_results_list,
        "edges": edges_list
    }


@router.get("/{scenario_id}")
def get_scenario(scenario_id: UUID, session: Session = Depends(get_session)):
    scenario = session.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    impacts = session.exec(select(ScenarioImpact).where(ScenarioImpact.scenario_id == scenario_id)).all()
    shock_results = session.exec(select(ShockResult).where(ShockResult.scenario_id == scenario_id)).all()

    return {
        "scenario": scenario,
        "impacts": [i.model_dump() for i in impacts],
        "shock_results": [s.model_dump() for s in shock_results]
    }