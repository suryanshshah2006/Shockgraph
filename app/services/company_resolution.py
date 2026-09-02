import re
import time
import yfinance as yf
from sqlmodel import Session, select

from app.models import Company, Relationship, ScenarioImpact, ShockResult
from app.services.llm_service import LLMServiceError, infer_company_relationships


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "company"


def _looks_like_ticker(query: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9.^=-]{1,12}", query.strip()))


from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

def _fetch_with_timeout(ticker_symbol, timeout_seconds=10):
    def _do_fetch():
        t = yf.Ticker(ticker_symbol)
        mc = t.fast_info.get("marketCap")
        if not mc:
            mc = t.info.get("marketCap")
        price = t.fast_info.get("lastPrice")
        if not price:
            price = t.info.get("currentPrice")
        return {
            "mc": mc,
            "price": price,
            "sector": t.info.get("sector"),
            "name": t.info.get("shortName") or t.info.get("longName")
        }

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_do_fetch)
    try:
        res = future.result(timeout=timeout_seconds)
        executor.shutdown(wait=False)
        return res
    except FutureTimeoutError:
        executor.shutdown(wait=False)
        return None

def _fetch_live_market_data(ticker_candidate: str, fallback_name: str) -> dict:
    """Fetch live market cap and details dynamically from Yahoo Finance without static mappings."""
    time.sleep(1.5)
    clean_ticker = ticker_candidate.strip().upper()
    metadata = {
        "ticker": clean_ticker,
        "name": fallback_name,
        "market_cap": None,
        "sector": None,
        "last_price": None,
    }

    # Add retry logic
    delays = [2, 4, 8]
    for attempt in range(4):
        try:
            res = _fetch_with_timeout(clean_ticker, timeout_seconds=10)
            if res and res.get("mc"):
                metadata["market_cap"] = res["mc"]
                metadata["last_price"] = res["price"]
                metadata["sector"] = res["sector"]
                if res["name"]:
                    metadata["name"] = res["name"]
                break
        except Exception as e:
            pass
            
        if attempt < 3:
            time.sleep(delays[attempt])

    return metadata


def find_company(session: Session, query: str, ticker: str | None = None) -> Company | None:
    query = query.strip()
    if ticker:
        ticker_upper = ticker.upper()
        ticker_match = session.exec(
            select(Company).where((Company.ticker == ticker_upper) | (Company.id == ticker_upper))
        ).first()
        if ticker_match:
            return ticker_match

    if not query:
        return None

    query_upper = query.upper()
    by_id_or_ticker = session.exec(
        select(Company).where((Company.ticker == query_upper) | (Company.id == query_upper))
    ).first()
    if by_id_or_ticker:
        return by_id_or_ticker

    return session.exec(select(Company).where(Company.name.ilike(query))).first()


def _create_company(session: Session, name: str, ticker_hint: str | None = None) -> Company:
    ticker_to_use = ticker_hint if ticker_hint else (name if _looks_like_ticker(name) else None)
    
    meta = {"ticker": None, "name": name, "market_cap": None, "sector": None, "last_price": None}
    if ticker_to_use:
        # _fetch_live_market_data might return the candidate ticker even if it fails to find data.
        fetched = _fetch_live_market_data(ticker_to_use, name)
        if fetched.get("market_cap") is not None or fetched.get("last_price") is not None:
            meta = fetched

    if meta.get("market_cap") is not None or meta.get("last_price") is not None:
        base_id = meta["ticker"]
    else:
        base_id = _slugify(name).upper()[:12]
        meta["ticker"] = None

    company_id = base_id
    suffix = 1
    while session.get(Company, company_id):
        suffix += 1
        company_id = f"{base_id}-{suffix}"

    company = Company(
        id=company_id,
        ticker=meta["ticker"],
        name=meta["name"],
        market_cap=meta["market_cap"],
        sector=meta["sector"],
        last_price=meta["last_price"],
    )
    session.add(company)
    session.flush()
    return company


def resolve_or_create_company(
    session: Session, query: str, ticker_hint: str | None = None, populate_relationships: bool = True
) -> Company:
    company = find_company(session, query, ticker=ticker_hint)
    
    if company:
        # Backfill market cap if previously missing
        ticker_to_fetch = company.ticker or ticker_hint
        if company.market_cap is None and ticker_to_fetch:
            meta = _fetch_live_market_data(ticker_to_fetch, company.name)
            if meta.get("market_cap"):
                company.market_cap = meta["market_cap"]
                company.last_price = meta["last_price"]
                company.sector = meta["sector"]
                company.ticker = meta["ticker"]
                session.add(company)
                session.flush()

        # Migrate stub (id != ticker) if it now has a real ticker and market cap
        if company.ticker and company.id != company.ticker and company.market_cap is not None:
            new_id = company.ticker
            existing_target = session.get(Company, new_id)
            
            if not existing_target:
                migrated = Company(
                    id=new_id,
                    ticker=company.ticker,
                    name=company.name,
                    market_cap=company.market_cap,
                    sector=company.sector,
                    last_price=company.last_price,
                    created_at=company.created_at,
                    last_refreshed=company.last_refreshed,
                )
                session.add(migrated)
                session.flush()
                target_company = migrated
            else:
                target_company = existing_target

            # Reassign relationships (supplier)
            for rel in session.exec(select(Relationship).where(Relationship.supplier_id == company.id)).all():
                existing = session.exec(select(Relationship).where(
                    Relationship.supplier_id == new_id,
                    Relationship.customer_id == rel.customer_id
                )).first()
                if existing:
                    keep_rel, drop_rel = (existing, rel)
                    if (rel.confidence or 0) > (existing.confidence or 0):
                        keep_rel, drop_rel = (rel, existing)
                    elif (rel.confidence or 0) == (existing.confidence or 0):
                        if rel.source == "filing" and existing.source != "filing":
                            keep_rel, drop_rel = (rel, existing)
                    
                    print(f"WARNING: Relationship collision for supplier={new_id}, customer={rel.customer_id}. Dropping row with source={drop_rel.source}, keeping source={keep_rel.source}.")
                    if keep_rel == rel:
                        rel.supplier_id = new_id
                        session.add(rel)
                        session.delete(existing)
                    else:
                        session.delete(rel)
                else:
                    rel.supplier_id = new_id
                    session.add(rel)

            # Reassign relationships (customer)
            for rel in session.exec(select(Relationship).where(Relationship.customer_id == company.id)).all():
                existing = session.exec(select(Relationship).where(
                    Relationship.supplier_id == rel.supplier_id,
                    Relationship.customer_id == new_id
                )).first()
                if existing:
                    keep_rel, drop_rel = (existing, rel)
                    if (rel.confidence or 0) > (existing.confidence or 0):
                        keep_rel, drop_rel = (rel, existing)
                    elif (rel.confidence or 0) == (existing.confidence or 0):
                        if rel.source == "filing" and existing.source != "filing":
                            keep_rel, drop_rel = (rel, existing)
                    
                    print(f"WARNING: Relationship collision for supplier={rel.supplier_id}, customer={new_id}. Dropping row with source={drop_rel.source}, keeping source={keep_rel.source}.")
                    if keep_rel == rel:
                        rel.customer_id = new_id
                        session.add(rel)
                        session.delete(existing)
                    else:
                        session.delete(rel)
                else:
                    rel.customer_id = new_id
                    session.add(rel)

            # Reassign ScenarioImpact
            for impact in session.exec(select(ScenarioImpact).where(ScenarioImpact.company_id == company.id)).all():
                existing = session.exec(select(ScenarioImpact).where(
                    ScenarioImpact.scenario_id == impact.scenario_id,
                    ScenarioImpact.company_id == new_id
                )).first()
                if existing:
                    print(f"WARNING: ScenarioImpact collision for scenario={impact.scenario_id}, company_id={new_id}. Dropping stub data from {company.id}.")
                    session.delete(impact)
                else:
                    impact.company_id = new_id
                    session.add(impact)

            # Reassign ShockResult
            for result in session.exec(select(ShockResult).where(ShockResult.company_id == company.id)).all():
                existing = session.exec(select(ShockResult).where(
                    ShockResult.scenario_id == result.scenario_id,
                    ShockResult.company_id == new_id
                )).first()
                if existing:
                    print(f"WARNING: ShockResult collision for scenario={result.scenario_id}, company_id={new_id}. Dropping stub data from {company.id}.")
                    session.delete(result)
                else:
                    result.company_id = new_id
                    session.add(result)

            session.delete(company)
            session.flush()
            company = target_company

        return company

    company = _create_company(session, query, ticker_hint=ticker_hint)

    if populate_relationships:
        try:
            related = infer_company_relationships(company.name)
        except LLMServiceError:
            related = []

        for item in related:
            rel_name = item["related_company_name"]
            rel_ticker = item.get("ticker")
            
            related_company = find_company(session, rel_name, ticker=rel_ticker)
            if related_company is None:
                related_company = _create_company(session, rel_name, ticker_hint=rel_ticker)

            if item["relationship_type"] == "supplier":
                supplier_id, customer_id = related_company.id, company.id
            else:
                supplier_id, customer_id = company.id, related_company.id

            existing_rel = session.exec(
                select(Relationship).where(
                    Relationship.supplier_id == supplier_id,
                    Relationship.customer_id == customer_id,
                )
            ).first()
            if existing_rel:
                continue

            session.add(
                Relationship(
                    supplier_id=supplier_id,
                    customer_id=customer_id,
                    weight=item["weight"],
                    relationship_type=item["relationship_type"],
                    source="gemini",
                    source_ref=item.get("source_explanation"),
                )
            )

        session.flush()

    return company


def find_or_fetch_company(
    session: Session, query: str, ticker_hint: str | None = None, populate_relationships: bool = True
) -> Company:
    return resolve_or_create_company(
        session, query, ticker_hint=ticker_hint, populate_relationships=populate_relationships
    )