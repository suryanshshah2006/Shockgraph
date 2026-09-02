# ⚡ ShockGraph

**See how far one shock actually travels.**

ShockGraph is a live financial contagion simulator. Describe a real-world
event in plain English — an export ban, a supplier embargo, a policy
shift — and watch it propagate through actual company dependencies,
tier by tier, priced in real dollar exposure.

Built for **Turing HackX** by **Team Taco**.

🔗 **Live demo:** [ADD_YOUR_RENDER_URL_HERE]

---

## The problem

When a real-world shock hits — a chip export ban, a raw material embargo,
a tariff — figuring out who's actually exposed means manually reading
news across dozens of tickers and guessing at second- and third-order
effects. Retail investors, analysts, and even risk desks mostly do this
by hand, with no systematic view of how exposure cascades through real
supply chains.

## What ShockGraph does

1. **You describe the event** — no tickers, no formatting, just plain
   language.
2. **An LLM resolves it against real companies** — every entity
   mentioned is matched to live market data before anything is
   calculated. Nothing is hardcoded; companies not yet in the database
   are resolved and cached live, so the dataset grows with every query.
3. **The cascade renders** — a dependency-weighted propagation engine
   traverses the graph from the epicenter outward, computing percent and
   dollar impact at each tier, rendered as an interactive network graph
   and a full exposure ledger.

## Architecture

Landing page (static HTML/CSS/JS)
│
▼
Terminal UI (Cytoscape.js graph + exposure ledger)
│ fetch()
▼
FastAPI backend
│
┌────┼─────────────┬──────────────┐
▼ ▼ ▼ ▼
PostgreSQL/ yfinance Gemini (structured
SQLite (live price & output) — scenario
(companies, market cap) classification &
edges, relationship
scenarios) extraction


## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Static HTML/CSS/JS, Cytoscape.js (hierarchical graph layout) |
| Backend | FastAPI, SQLModel |
| Database | PostgreSQL (SQLite for local dev) |
| Market data | yfinance |
| Reasoning | Google Gemini, structured output via Pydantic schemas |
| Data sources | SEC EDGAR (US filings), NSE/BSE disclosures (Indian equities) |

## Why this isn't just a hardcoded graph

Every company relationship stored in the database carries a `source`
(filing-derived or LLM-inferred) and a `confidence` score — low-confidence
inferred edges are never presented as verified fact. Companies not yet
seen are resolved live against real market data on first mention and
cached for every query after, rather than pulled from a fixed list.

## Research grounding

The propagation model draws on published work on financial network
contagion, not an invented heuristic:

- Elliott, M., Golub, B., and Jackson, M. O. (2014). *Financial Networks
  and Contagion.* American Economic Review, 104(10), 3115–3153.
- Acemoglu, D., Ozdaglar, A., and Tahbaz-Salehi, A. (2015). *Systemic
  Risk and Stability in Financial Networks.* American Economic Review,
  105(2), 564–608.

## Running locally

```bash
git clone https://github.com/<your-username>/shockgraph.git
cd shockgraph

python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# create a .env file with:
# GEMINI_API_KEY=your_key_here

uvicorn app.main:app --port 8000
```

Then open **http://127.0.0.1:8000/** — the landing page and terminal are
served directly by the FastAPI app.

## API

| Endpoint | Description |
|---|---|
| `POST /scenarios` | Submit a plain-text event, get back the full cascade |
| `GET /companies` | List all resolved companies |
| `GET /companies/{id}` | Get a single company's details |
| `POST /companies/resolve` | Resolve a company by name/ticker on demand |

## Team Taco

- **Suryansh Shah** — Lead
- **Shreya Sinha**

Built for Turing HackX · Theme: FinTech & Risk AI
