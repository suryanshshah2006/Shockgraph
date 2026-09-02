import streamlit as st
import requests
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="ShockGraph Simulator", page_icon="⚡")

st.markdown("""
<style>
    .metric-card {
        background-color: #1E222B;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #FF4B4B;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ ShockGraph: Live Supply Chain Contagion Simulator")
st.markdown("Enter any macroeconomic disruption, regulatory ban, or corporate shock to compute propagation depths and dollar losses across global & Indian equities.")

col_input, col_preset = st.columns([3, 1])

with col_input:
    scenario_text = st.text_input(
        "Macroeconomic / Supply Chain Event:",
        "TSMC halts advanced 3nm semiconductor deliveries due to geopolitical restrictions, cutting supply by 25%."
    )

with col_preset:
    st.write("Preset Scenarios")
    if st.button("🇮🇳 Tata Motors EV Battery Shock"):
        scenario_text = "Tata Motors faces critical Lithium-ion battery supplier embargo causing 18% production drop."
    if st.button("🇺🇸 Nvidia Export Block"):
        scenario_text = "Nvidia halts advanced AI GPU shipments worldwide causing a 20% direct shock."

if st.button("🚀 Run Contagion Simulation", type="primary"):
    with st.spinner("Classifying shock, querying live NSE/BSE/US market caps, and evaluating graph topology..."):
        try:
            response = requests.post("http://127.0.0.1:8000/scenarios", params={"payload": scenario_text})
            
            if response.status_code != 200:
                st.error(f"Backend Error: {response.text}")
            else:
                data = response.json()
                shock_results = data.get("shock_results", [])
                edges = data.get("edges", [])
                
                if not shock_results:
                    st.warning("No linked companies detected. Try a query mentioning specific firms, sectors, or raw materials.")
                else:
                    # Metric Summary Bar
                    total_dollar_loss = sum(r["dollar_impact"] for r in shock_results if r["dollar_impact"] and r["dollar_impact"] < 0)
                    max_depth = max(r["depth"] for r in shock_results)
                    epicenter = [r["name"] for r in shock_results if r.get("is_epicenter")]
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Shock Origin (Epicenter)", epicenter[0] if epicenter else "Identified", delta="Epicenter Node", delta_color="inverse")
                    m2.metric("Total Market Cap at Risk", f"${abs(total_dollar_loss)/1e9:.2f}B" if total_dollar_loss else "Live Resolving", delta="Cascading Exposure", delta_color="inverse")
                    m3.metric("Contagion Depth", f"Tier {max_depth}", "Recursive Propagation")
                    m4.metric("Entities Impacted", f"{len(shock_results)} Companies", f"{len(edges)} Supply Edges")

                    st.markdown("---")
                    st.subheader("🌐 Interactive Contagion Network Map")

                    # PyVis Graph Setup
                    net = Network(height="650px", width="100%", bgcolor="#0F1117", font_color="#FFFFFF", directed=True)
                    
                    added_nodes = set()
                    cleaned_rows = []

                    for res in shock_results:
                        company_id = res["company_id"]
                        name = res.get("name", company_id)
                        ticker = res.get("ticker", company_id)
                        impact_pct = res["total_impact_pct"]
                        dollar_impact = res["dollar_impact"]
                        depth = res["depth"]
                        sector = res.get("sector", "Equities")
                        is_epicenter = res.get("is_epicenter", False)
                        
                        # Dynamic Styling based on Shock Role
                        if is_epicenter:
                            node_color = "#D90429"
                            border_color = "#FFD166"
                            shape = "diamond"
                            size = 45
                        elif impact_pct <= -10:
                            node_color = "#EF233C"
                            border_color = "#FFFFFF"
                            shape = "dot"
                            size = 32
                        elif impact_pct < 0:
                            node_color = "#FF758F"
                            border_color = "#FFFFFF"
                            shape = "dot"
                            size = 24
                        else:
                            node_color = "#06D6A0"
                            border_color = "#FFFFFF"
                            shape = "dot"
                            size = 22
                        
                        formatted_dollar = f"${dollar_impact/1e9:,.2f}B" if dollar_impact and abs(dollar_impact) >= 1e9 else (f"${dollar_impact/1e6:,.2f}M" if dollar_impact else "N/A")
                        
                        label_display = f"{ticker}\n({impact_pct:+.1f}%)"
                        tooltip = f"""
                        <div style='font-family: sans-serif; padding: 6px;'>
                            <b>{name} ({ticker})</b><br/>
                            <b>Sector:</b> {sector}<br/>
                            <b>Contagion Tier:</b> Depth {depth}<br/>
                            <b>Shock Impact:</b> {impact_pct:+.2f}%<br/>
                            <b>Valuation Exposure:</b> {formatted_dollar}
                        </div>
                        """
                        
                        net.add_node(
                            company_id,
                            label=label_display,
                            title=tooltip,
                            color={"background": node_color, "border": border_color, "highlight": "#FFFFFF"},
                            borderWidth=3 if is_epicenter else 1,
                            shape=shape,
                            size=size,
                            font={"color": "#FFFFFF", "size": 13, "face": "Helvetica"}
                        )
                        added_nodes.add(company_id)
                        
                        cleaned_rows.append({
                            "Ticker": ticker,
                            "Company Name": name,
                            "Sector": sector,
                            "Contagion Tier": f"Depth {depth}",
                            "Impact (%)": f"{impact_pct:+.2f}%",
                            "Dollar Loss ($)": formatted_dollar,
                        })

                    # Add Edges with dependency weight labels
                    for edge in edges:
                        u, v = edge["from"], edge["to"]
                        if u in added_nodes and v in added_nodes:
                            weight = edge.get("weight", 0.5)
                            rel_type = edge.get("relationship_type", "supplies")
                            source_info = edge.get("source_ref", "Supply dependency")
                            
                            edge_label = f"{weight*100:.0f}%"
                            edge_tooltip = f"<b>Flow:</b> {u} ➔ {v}<br/><b>Type:</b> {rel_type}<br/><b>Weight:</b> {weight*100:.0f}%<br/><b>Context:</b> {source_info}"
                            
                            net.add_edge(
                                u,
                                v,
                                title=edge_tooltip,
                                label=edge_label,
                                value=max(weight * 3, 1),
                                color={"color": "#6C757D", "highlight": "#FFD166"},
                                arrows={"to": {"enabled": True, "scaleFactor": 1.1}},
                                font={"color": "#ADB5BD", "size": 10, "align": "middle"}
                            )

                    # Smooth Physics & Layout Configuration
                    net.set_options("""
                    var options = {
                      "nodes": {
                        "shadow": true
                      },
                      "edges": {
                        "smooth": {
                          "type": "cubicBezier",
                          "forceDirection": "horizontal",
                          "roundness": 0.3
                        },
                        "shadow": true
                      },
                      "physics": {
                        "forceAtlas2Based": {
                          "gravitationalConstant": -60,
                          "centralGravity": 0.01,
                          "springLength": 100,
                          "springConstant": 0.08
                        },
                        "minVelocity": 0.75,
                        "solver": "forceAtlas2Based"
                      }
                    }
                    """)
                    
                    net.save_graph("pyvis_graph.html")
                    with open("pyvis_graph.html", 'r', encoding='utf-8') as f:
                        components.html(f.read(), height=670, scrolling=False)
                    
                    st.markdown("---")
                    st.subheader("📋 Cascading Exposure Ledger")
                    df = pd.DataFrame(cleaned_rows)
                    st.dataframe(df, use_container_width=True)

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend server. Make sure `uvicorn app.main:app --reload` is running on port 8000.")
        except Exception as e:
            st.error(f"UI Rendering Error: {e}")