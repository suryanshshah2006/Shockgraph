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
