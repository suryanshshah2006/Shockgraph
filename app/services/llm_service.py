from __future__ import annotations

import logging
import os
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class LLMServiceError(RuntimeError):
    """Raised when a Gemini call fails or returns a response that doesn't match the schema."""


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMServiceError("GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)


class ScenarioImpactItem(BaseModel):
    company_query: str
    ticker: str = Field(
        description="Official Yahoo Finance ticker symbol. For Indian NSE companies, append .NS (e.g., TATAMOTORS.NS, RELIANCE.NS, TCS.NS). For US, use standard ticker (e.g., NVDA, AAPL, TSM)."
    )
    direct_shock_pct: float
    reasoning: str


class ScenarioExtraction(BaseModel):
    scenario_type: Literal["chain_shock", "event_shock"]
    impacts: list[ScenarioImpactItem]


def extract_scenario_impacts(prompt: str) -> dict:
    """Classify a scenario prompt and extract directly impacted companies with valid tickers."""
    client = _get_client()
    system_instruction = (
        "You are a financial analyst extracting structured supply-chain shock data from news or event descriptions. "
        "Classify the scenario as 'chain_shock' (disruption propagating through dependencies) or 'event_shock' (isolated event). "
        "For every company directly impacted, identify its exact Yahoo Finance ticker (append '.NS' for Indian NSE equities, '.BO' for BSE). Note: Tata Motors has demerged; always use 'TMPV.NS' instead of the defunct 'TATAMOTORS.NS'. "
        "Estimate the direct percentage impact (negative for adverse, positive for beneficial) and provide brief reasoning."
    )

    try:
        response = client.models.generate_content(
            model=_DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ScenarioExtraction,
            ),
        )
    except Exception as exc:
        logger.exception("Gemini call failed for scenario extraction")
        raise LLMServiceError(f"Gemini call failed for scenario extraction: {exc}") from exc

    parsed: ScenarioExtraction | None = response.parsed
    if parsed is None:
        raise LLMServiceError(f"Gemini returned an invalid schema: {response.text!r}")

    return {
        "scenario_type": parsed.scenario_type,
        "impacts": [item.model_dump() for item in parsed.impacts],
    }


class RelatedCompany(BaseModel):
    related_company_name: str
    ticker: str = Field(
        description="Official Yahoo Finance ticker. Append .NS for Indian NSE equities (e.g., BOSCHLTD.NS, TATAELXSI.NS, MOTHERSON.NS, SONACOMS.NS) or .BO for BSE."
    )
    relationship_type: Literal["supplier", "customer"]
    weight: float = Field(ge=0.1, le=0.9, description="Dependency weight between 0.1 and 0.9")
    source_explanation: str


class CompanyRelationships(BaseModel):
    relationships: list[RelatedCompany]


def infer_company_relationships(company_name: str) -> list[dict]:
    """Infer comprehensive suppliers and enterprise customers, including Indian subsidiaries and niche suppliers."""
    client = _get_client()
    system_instruction = (
        "You are a global supply-chain and equity research analyst specializing in global tech and Indian corporate structures (NSE/BSE). "
        "Given a company, identify ALL significant suppliers and enterprise customers based on public filings, annual reports, and industry linkages. "
        "Do not artificially restrict the list; include all major as well as publicly traded niche suppliers/customers (including those traded on NSE/BSE/Groww/Zerodha). "
        "For Indian conglomerates (e.g., Tata, Reliance, Mahindra, Adani, L&T), resolve specific operating subsidiaries (e.g., Tata Motors -> TMPV.NS, Tata Steel, Tata Elxsi, Sona BLW, Bharat Forge). "
        "EXPLICITLY EXCLUDE countries, geographic regions (e.g., 'Taiwan', 'Europe'), generic sectors (e.g., 'Semiconductors', 'Auto'), or industry groups. "
        "ONLY extract real publicly-traded or specifically named private companies. "
        "Always provide the valid Yahoo Finance ticker symbol (append '.NS' or '.BO' for Indian equities). Note: Tata Motors has demerged; always use 'TMPV.NS' instead of the defunct 'TATAMOTORS.NS'. "
        "Assign an estimated dependency weight between 0.1 and 0.9 and a short source explanation."
    )

    try:
        response = client.models.generate_content(
            model=_DEFAULT_MODEL,
            contents=f"Company: {company_name}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=CompanyRelationships,
            ),
        )
    except Exception as exc:
        logger.exception("Gemini call failed for relationship inference on %r", company_name)
        raise LLMServiceError(f"Gemini call failed for relationship inference on {company_name!r}: {exc}") from exc

    parsed: CompanyRelationships | None = response.parsed
    if parsed is None:
        raise LLMServiceError(f"Gemini returned an invalid schema: {response.text!r}")

    return [item.model_dump() for item in parsed.relationships]