from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid

class Company(SQLModel, table=True):
    __tablename__ = "companies"
    id: str = Field(primary_key=True)
    ticker: Optional[str] = None
    name: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None
    last_price: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_refreshed: Optional[datetime] = None

class CompanyRelationship(SQLModel, table=True):
    __tablename__ = "relationships"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    supplier_id: str = Field(foreign_key="companies.id")
    customer_id: str = Field(foreign_key="companies.id")
    weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    relationship_type: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    source_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Scenario(SQLModel, table=True):
    __tablename__ = "scenarios"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    raw_text: Optional[str] = None
    scenario_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ScenarioImpact(SQLModel, table=True):
    __tablename__ = "scenario_impacts"
    scenario_id: uuid.UUID = Field(foreign_key="scenarios.id", primary_key=True)
    company_id: str = Field(foreign_key="companies.id", primary_key=True)
    direct_shock_pct: Optional[float] = None
    reasoning: Optional[str] = None

class ShockResult(SQLModel, table=True):
    __tablename__ = "shock_results"
    scenario_id: uuid.UUID = Field(foreign_key="scenarios.id", primary_key=True)
    company_id: str = Field(foreign_key="companies.id", primary_key=True)
    total_impact_pct: Optional[float] = None
    dollar_impact: Optional[float] = None
    depth: Optional[int] = None
