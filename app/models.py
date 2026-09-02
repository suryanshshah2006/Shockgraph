from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: str = Field(primary_key=True)
    ticker: str = Field(index=True)
    name: str
    country: str | None = None
    sector: str | None = None
    exchange: str | None = None
    market_cap: float | None = None
    last_price: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_refreshed: datetime | None = None


class Relationship(SQLModel, table=True):
    __tablename__ = "relationships"
    __table_args__ = (CheckConstraint("weight >= 0.0 AND weight <= 1.0", name="weight_range"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    supplier_id: str = Field(foreign_key="companies.id", index=True)
    customer_id: str = Field(foreign_key="companies.id", index=True)
    weight: float
    relationship_type: str | None = None
    source: str | None = None
    confidence: float | None = None
    source_ref: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Scenario(SQLModel, table=True):
    __tablename__ = "scenarios"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    raw_text: str
    scenario_type: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScenarioImpact(SQLModel, table=True):
    __tablename__ = "scenario_impacts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    scenario_id: UUID = Field(foreign_key="scenarios.id", index=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    direct_shock_pct: float
    reasoning: str | None = None


class ShockResult(SQLModel, table=True):
    __tablename__ = "shock_results"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    scenario_id: UUID = Field(foreign_key="scenarios.id", index=True)
    company_id: str = Field(foreign_key="companies.id", index=True)
    total_impact_pct: float
    dollar_impact: float | None = None
    depth: int
