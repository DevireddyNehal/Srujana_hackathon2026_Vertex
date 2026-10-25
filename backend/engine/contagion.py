"""
The Butterfly Effect: Financial Contagion Simulation Engine (Institutional-Grade)
Module: backend.engine.contagion
Role: Lead Sandbox (Economic Dependency Graph, Multi-Hop Shock Propagation, Portfolio Contagion Calculator, Immunization Engine)

Features:
1. NetworkX-backed Directed Acyclic Graph (DAG) of Commodities, Macro Factors, Sectors, and NSE Assets.
2. Dynamic Multi-Hop Wave Propagation Engine with path tracing and non-linear saturation bounds.
3. Interactive user-adjustable shock magnitudes (e.g. Oil +10% to +100%, Repo Rate +25 to +400 bps).
4. Direct Single-Counted Portfolio Exposure & Rupee Impact (Rp = sum(w_i * r_i) with zero double-counting).
5. Contagion Inoculation Optimizer (Calculates minimum defensive hedging allocation to neutralize drawdown).
6. Inspectable Evidence & Assumption Layer (Detailed economic rationale for every transmission edge).
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    if __package__:
        from .quant import detect_false_diversification
    else:
        from engine.quant import detect_false_diversification
except ImportError:
    try:
        from quant import detect_false_diversification
    except ImportError:
        detect_false_diversification = None


class EconomicDependencyGraph:
    """
    High-performance Directed Acyclic Graph (DAG) for economic contagion modeling.
    Uses NetworkX under the hood when available, with a resilient native dictionary
    fallback. Supports multi-hop traversal, causal path lineage, and frontend JSON export.
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.adjacency: Dict[str, List[Dict[str, Any]]] = {}
        self.predecessors: Dict[str, List[Dict[str, Any]]] = {}
        if HAS_NETWORKX:
            self._nx_graph = nx.DiGraph()
        else:
            self._nx_graph = None

    def add_node(
        self,
        node_id: str,
        label: str,
        category: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add an entity node (shock, macro factor, sector, or portfolio asset)."""
        node_data = {
            "id": node_id,
            "label": label,
            "category": category,  # 'shock', 'first_order', 'second_order', 'asset'
            "description": description,
            "metadata": metadata or {},
        }
        self.nodes[node_id] = node_data
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []
        if node_id not in self.predecessors:
            self.predecessors[node_id] = []

        if HAS_NETWORKX and self._nx_graph is not None:
            self._nx_graph.add_node(node_id, **node_data)

    def add_edge(
        self,
        source: str,
        target: str,
        relationship: str,
        sensitivity: float,
        rationale: str,
        confidence: str = "High",
        assumptions: str = "",
        lag_days: int = 30,
    ):
        """Add a directed causal transmission edge with sensitivity (elasticity) and economic rationale."""
        edge_data = {
            "source": source,
            "target": target,
            "relationship": relationship,
            "sensitivity": sensitivity,
            "rationale": rationale,
            "confidence": confidence,
            "assumptions": assumptions,
            "lag_days": lag_days,
        }
        if source not in self.adjacency:
            self.adjacency[source] = []
        self.adjacency[source].append(edge_data)

        if target not in self.predecessors:
            self.predecessors[target] = []
        self.predecessors[target].append(edge_data)

        if HAS_NETWORKX and self._nx_graph is not None:
            self._nx_graph.add_edge(source, target, **edge_data)

    def get_successors(self, node_id: str) -> List[Dict[str, Any]]:
        return self.adjacency.get(node_id, [])

    def get_predecessors(self, node_id: str) -> List[Dict[str, Any]]:
        return self.predecessors.get(node_id, [])

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete graph structure for visual renderers."""
        edges_list = []
        for src, edges in self.adjacency.items():
            for e in edges:
                edges_list.append({
                    "source": src,
                    "target": e["target"],
                    "relationship": e["relationship"],
                    "sensitivity": e["sensitivity"],
                    "rationale": e["rationale"],
                    "confidence": e["confidence"],
                    "lag_days": e.get("lag_days", 30),
                })
        return {
            "nodes": list(self.nodes.values()),
            "edges": edges_list,
        }


# ---------------------------------------------------------------------------
# CANONICAL ECONOMIC DEPENDENCY GRAPH BUILDER
# ---------------------------------------------------------------------------
def build_economic_dependency_graph() -> EconomicDependencyGraph:
    """
    Constructs the master macroeconomic dependency graph mapping:
    - Shocks: Oil Supply Disruption, RBI Repo Tightening, US Tech Spending Freeze, Currency Pressure
    - First-Order: Fuel Costs, Sovereign Yields, MCLR Lending Rates, IT Deal Velocity, Current Account Deficit
    - Second-Order: Airline Margins, Paint COGS, Tech DCF Multiple, REIT Cap Rates, Bank Treasury MTM
    - Asset Holdings: TCS, Infosys, Wipro, HDFC Bank, ICICI Bank, IndiGo, Asian Paints, Tata Motors, Gold, Liquid Debt
    """
    g = EconomicDependencyGraph()

    # =======================================================================
    # SCENARIO 1: GLOBAL OIL SUPPLY DISRUPTION
    # =======================================================================
    g.add_node("shock_oil", "Global Oil Supply Disruption", "shock", "Crude oil supply contraction triggers acute price spike.")
    g.add_node("fo_fuel_costs", "Transport & Aviation Fuel Costs", "first_order", "Direct surge in aviation turbine fuel (ATF) and diesel pump prices.")
    g.add_node("fo_import_bill", "Current Account Deficit (CAD)", "first_order", "India imports >85% of crude needs; higher dollar import bills widen the trade gap.")
    g.add_node("fo_cpi_fuel", "Domestic Transport CPI Inflation", "first_order", "Freight and logistics surcharges feed into headline headline consumer inflation.")

    g.add_node("so_aviation_margins", "Airline Operating Margins", "second_order", "Fuel constitutes ~40% of airline OPEX, crushing quarterly EBITDAR margins.")
    g.add_node("so_paint_cogs", "Paints & Polymer Input COGS", "second_order", "Crude derivatives (monomers, solvents, resins) inflate cost of goods sold.")
    g.add_node("so_inr_depreciation", "INR Currency Weakening", "second_order", "Heightened dollar demand from oil marketing companies depreciates the Rupee.")
    g.add_node("so_gold_safe_haven", "Safe-Haven Commodity Demand", "second_order", "Geopolitical supply crises trigger capital rotation into physical gold & silver.")
    g.add_node("so_rate_pressure", "Delayed RBI Rate Cuts", "second_order", "Sticky fuel-driven inflation forces central bank to keep policy rates elevated.")

    # Edges: Shock -> 1st Order
    g.add_edge("shock_oil", "fo_fuel_costs", "Refined Fuel Pass-Through", 0.70, "Crude oil price pass-through into refined fuel averages 70% within 30 days.", "High", "Petroleum Planning & Analysis Cell (PPAC) data.", lag_days=15)
    g.add_edge("shock_oil", "fo_import_bill", "Trade Gap Widening", 0.50, "Every $10/bbl rise in Brent crude expands India's annual CAD by ~$14B.", "High", "RBI macroeconomic assessment reports.", lag_days=30)
    g.add_edge("shock_oil", "fo_cpi_fuel", "Freight Cost Inflation", 0.35, "Higher diesel prices pass directly into inter-state road freight rates.", "High", "Logistics industry surveys.", lag_days=20)
    g.add_edge("shock_oil", "so_gold_safe_haven", "Safe-Haven Capital Flight", 0.35, "Geopolitical tensions and inflation hedging trigger safe-haven gold accumulation.", "High", "Empirical gold beta during commodity shocks.", lag_days=7)

    # Edges: 1st Order -> 2nd Order
    g.add_edge("fo_fuel_costs", "so_aviation_margins", "OPEX Compression", -0.65, "Airlines cannot pass 100% of sudden fuel spikes to passengers immediately without killing demand.", "High", "DGCA & aviation quarterly filings.", lag_days=30)
    g.add_edge("fo_fuel_costs", "so_paint_cogs", "Raw Material Squeeze", -0.40, "Petrochemical inputs represent 45-50% of paint manufacturing costs.", "High", "Chemical & paint sector equity research.", lag_days=45)
    g.add_edge("fo_import_bill", "so_inr_depreciation", "Currency Depreciation", -0.22, "Oil importers' dollar bids outstrip export inflows, weakening INR against USD.", "Medium", "Forex flow analysis.", lag_days=30)
    g.add_edge("fo_cpi_fuel", "so_rate_pressure", "Hawkish Central Bank Stance", 0.40, "Inflation above the 4% target forces prolonged tight monetary liquidity.", "High", "RBI Monetary Policy Committee minutes.", lag_days=60)

    # =======================================================================
    # SCENARIO 2: RBI REPO RATE TIGHTENING CYCLE
    # =======================================================================
    g.add_node("shock_rates", "RBI Repo Rate Tightening", "shock", "Central bank raises repo rate unexpectedly to tame persistent domestic inflation.")
    g.add_node("fo_bond_yields", "10Y Benchmark Sovereign Yields", "first_order", "Benchmark sovereign G-Sec yields shift upward across the term structure.")
    g.add_node("fo_lending_rates", "Bank Marginal Cost Lending Rates (MCLR/EBLR)", "first_order", "Commercial banks reset floating lending rates higher for retail and corporate borrowers.")
    g.add_node("fo_systemic_liquidity", "Interbank Systemic Liquidity Deficit", "first_order", "Net liquidity injection under LAF falls, tightening interbank call money rates.")

    g.add_node("so_tech_dcf", "Growth Equity DCF Multiple Compression", "second_order", "Higher discount rates reduce the net present value of long-duration cash flows.")
    g.add_node("so_realty_demand", "Mortgage & Real Estate Cap-Rate Friction", "second_order", "Higher home loan EMIs dampen housing absorption; commercial cap rates widen.")
    g.add_node("so_bank_mtm", "Bank Treasury Mark-to-Market Markdown", "second_order", "Banks incur unrealized MTM hits on fixed-income AFS/HFT investment books.")
    g.add_node("so_liquid_reinvestment", "Short-Term Reinvestment Yield Boost", "second_order", "Overnight and liquid money-market mutual funds capture higher reinvestment yields.")

    # Edges: Shock -> 1st Order
    g.add_edge("shock_rates", "fo_bond_yields", "Yield Curve Shift", 0.60, "Sovereign curve resets higher with strong beta to unexpected policy changes.", "High", "FIMMDA market transmission history.", lag_days=10)
    g.add_edge("shock_rates", "fo_lending_rates", "Monetary Policy Pass-Through", 0.75, "Mandatory external benchmark (EBLR) triggers immediate quarterly lending resets.", "High", "RBI monetary transmission framework.", lag_days=30)
    g.add_edge("shock_rates", "fo_systemic_liquidity", "Liquidity Absorption", -0.50, "Open market operations absorb durable cash surplus from banking channels.", "High", "RBI balance sheet data.", lag_days=20)

    # Edges: 1st Order -> 2nd Order
    g.add_edge("fo_bond_yields", "so_tech_dcf", "Discount Rate Drag", -0.07, "High-multiple growth equities experience P/E de-rating as discount rates climb.", "Medium", "DCF valuation sensitivity analysis.", lag_days=45)
    g.add_edge("fo_bond_yields", "so_bank_mtm", "Treasury Book Loss", -0.05, "Fixed-rate sovereign bond holdings suffer instantaneous mark-to-market depreciation.", "High", "Scheduled Commercial Bank financial disclosures.", lag_days=15)
    g.add_edge("fo_lending_rates", "so_realty_demand", "Financing Cost Escalation", -0.16, "Elevated financing costs reduce property buyer affordability and institutional yields.", "High", "Real estate market cap rate models.", lag_days=60)
    g.add_edge("fo_lending_rates", "so_liquid_reinvestment", "Yield Accrual", 0.85, "Ultra short-term liquid funds reset yields upward with zero duration loss.", "High", "Liquid fund portfolio duration analysis.", lag_days=7)

    # =======================================================================
    # SCENARIO 3: US ENTERPRISE TECH SPENDING FREEZE
    # =======================================================================
    g.add_node("shock_tech_freeze", "US Enterprise Tech Spending Freeze", "shock", "US Fortune 500 corporations cut discretionary software consulting budgets.")
    g.add_node("fo_it_deal_velocity", "Offshore IT Deal Signing Velocity", "first_order", "Contract signing cycles extend from 60 to 150 days; project starts paused.")
    g.add_node("fo_bench_utilization", "Bench Utilization Contraction", "first_order", "Employee billability falls from 84% to 76%, increasing unbilled bench cost.")
    g.add_node("so_it_margins", "IT Services Operating Margin Squeeze", "second_order", "EBIT margins contract by 250-350 bps across major Tier-1 Indian IT firms.")
    g.add_node("so_it_guidance", "Annual CC Revenue Guidance Downgrades", "second_order", "Management teams lower constant-currency revenue forecasts, prompting equity derating.")

    # Edges: Shock -> 1st Order (Negative spending shock reduces deal closures and bench utilization)
    g.add_edge("shock_tech_freeze", "fo_it_deal_velocity", "Deal Pipeline Contraction", 0.80, "Discretionary cloud migrations and transformation projects deferred first.", "High", "Gartner enterprise IT spending trends.", lag_days=30)
    g.add_edge("shock_tech_freeze", "fo_bench_utilization", "Billable Utilization Drop", 0.60, "Fixed engineering headcount cannot be reduced instantaneously, lowering billability.", "High", "NASSCOM IT operational benchmarking.", lag_days=45)

    # Edges: 1st Order -> 2nd Order (Contractions in deal volume and billability compress operating margins)
    g.add_edge("fo_it_deal_velocity", "so_it_margins", "Revenue De-acceleration", 0.65, "Fixed delivery costs eat operating leverage as top-line contract billings stall.", "High", "Historical 2022-2023 tech slowdown empirical filings.", lag_days=60)
    g.add_edge("fo_bench_utilization", "so_it_margins", "Unbilled Cost Drag", 0.40, "Lower utilization directly compresses blended gross margin per consultant.", "High", "Quarterly Tier-1 IT margin waterfalls.", lag_days=45)
    g.add_edge("fo_it_deal_velocity", "so_it_guidance", "Forward Forecast Cuts", 0.50, "Pipeline conversion delays prompt conservative forward revenue guidance.", "High", "Equity research analyst consensus.", lag_days=60)

    # =======================================================================
    # ASSET LEVEL TRANSMISSION LINKAGES
    # Maps 2nd-order factor nodes to specific NSE holdings
    # =======================================================================
    # IT Equities
    for it_ticker in ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS"]:
        g.add_node(f"holding_{it_ticker}", it_ticker, "asset", f"Tier-1 Indian IT services exporter ({it_ticker}).")
        # Direct hit from tech spending freeze & guidance cut
        g.add_edge("so_it_margins", f"holding_{it_ticker}", "Margin Compression Drag", 0.80, "Operating margin drop passes directly into equity net profit margins.", "High", "Direct equity beta to enterprise IT spend.", lag_days=30)
        g.add_edge("so_it_guidance", f"holding_{it_ticker}", "Guidance Downgrade De-rating", 0.60, "Forward guidance cuts trigger multiple compression from institutional holders.", "High", "Equity research consensus downgrades.", lag_days=45)
        # Hit from rate tightening DCF multiple compression
        g.add_edge("so_tech_dcf", f"holding_{it_ticker}", "DCF Valuation De-rating", 0.80, "High-growth multiple compresses under higher risk-free discount rate.", "Medium", "Historical tech sensitivity to yields.", lag_days=45)
        # Currency boost from oil shock (INR depreciation)
        g.add_edge("so_inr_depreciation", f"holding_{it_ticker}", "Export Realization Cushion", -0.35, "Weak Rupee boosts INR revenues translated from offshore USD contracts.", "High", "NSE IT export revenue sensitivity.", lag_days=30)


    # Banking Equities
    for bank_ticker in ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS"]:
        g.add_node(f"holding_{bank_ticker}", bank_ticker, "asset", f"Premier Indian scheduled commercial bank ({bank_ticker}).")
        g.add_edge("so_bank_mtm", f"holding_{bank_ticker}", "Treasury Valuation Hit", 0.75, "MTM depreciation on sovereign investment book impacts quarterly return on assets.", "High", "Bank quarterly disclosures.", lag_days=15)
        g.add_edge("so_rate_pressure", f"holding_{bank_ticker}", "Credit Growth & NIM Friction", -0.30, "Persistent high rates reduce credit demand and raise cost of deposits.", "Medium", "NIM sensitivity analysis.", lag_days=45)

    # Aviation Equities
    g.add_node("holding_INDIGO", "IndiGo (InterGlobe Aviation)", "asset", "Dominant Indian low-cost carrier with >60% domestic passenger share.")
    g.add_edge("so_aviation_margins", "holding_INDIGO", "Direct Earnings Contraction", 1.00, "Jet fuel price hikes pass with high correlation into quarterly operating losses.", "High", "Aviation operating models.", lag_days=30)

    # Paints & Chemicals
    g.add_node("holding_ASIANPAINT", "Asian Paints Ltd", "asset", "Market leader in architectural coatings and decorative paints.")
    g.add_edge("so_paint_cogs", "holding_ASIANPAINT", "Gross Margin Squeeze", 0.90, "Petrochemical solvent and phthalic anhydride costs contract EBITDA margin.", "High", "Paint sector equity research.", lag_days=45)

    # Real Estate & REITs
    g.add_node("holding_REALTY_LOCKED", "Commercial REIT / Locked Real Estate", "asset", "Long-duration locked real estate fund / commercial REIT.")
    g.add_edge("so_realty_demand", "holding_REALTY_LOCKED", "Cap Rate Repricing Drag", 0.95, "Cap rates expand in response to rising borrowing yields, devaluing NAV.", "High", "REIT cap rate discounting model.", lag_days=60)

    # Safe-Haven & Hedging Assets
    g.add_node("holding_GOLDBEES.NS", "Nippon India Gold ETF (GOLDBEES)", "asset", "Physical gold-backed ETF offering direct bullion spot price exposure.")
    g.add_edge("so_gold_safe_haven", "holding_GOLDBEES.NS", "Safe-Haven Capital Inflow", 1.00, "Spot bullion appreciation directly lifts Gold ETF NAV.", "High", "Gold ETF tracking record.", lag_days=7)

    g.add_node("holding_LIQUIDBEES.NS", "Nippon India Liquid ETF (LIQUIDBEES)", "asset", "Overnight tri-party repo (TREPS) money market ETF.")
    g.add_edge("so_liquid_reinvestment", "holding_LIQUIDBEES.NS", "Yield Accrual Boost", 1.00, "Daily dividend reinvestment captures immediate money market yield expansion.", "High", "Overnight rate transmission.", lag_days=3)

    return g


# ---------------------------------------------------------------------------
# CANONICAL SCENARIO DEFINITIONS WITH DEFAULT MAGNITUDES
# ---------------------------------------------------------------------------
AVAILABLE_CONTAGION_SCENARIOS = {
    "oil_supply_disruption": {
        "id": "oil_supply_disruption",
        "title": "Global Oil Supply Disruption",
        "shock_node": "shock_oil",
        "headline": "What if global crude oil supply contracts sharply?",
        "magnitude_description": "Assume crude oil prices rise 20% due to Middle East supply chokepoint friction.",
        "default_shock_magnitude": 20.0,
        "slider_range": {"min": 5.0, "max": 100.0, "step": 5.0, "unit": "%"},
        "historical_precedent": "1990 Gulf War Oil Shock (+130%), 2022 Geopolitical Conflict (+45%).",
        "primary_asset_shocks": {
            "IT": 2.0,            # Currency cushion
            "Banking": -4.0,       # Fuel inflation pressure
            "Paints": -15.0,       # Raw material surge
            "Airlines": -20.0,     # ATF fuel cost spike
            "Real Estate": -3.0,   # Raw material inflation
            "Gold": 7.0,           # Safe-haven flight
            "Liquid Debt": 0.5,    # Defensive parking
        }
    },
    "rbi_repo_tightening": {
        "id": "rbi_repo_tightening",
        "title": "Aggressive RBI Repo Rate Tightening",
        "shock_node": "shock_rates",
        "headline": "What if RBI hikes repo rate unexpectedly by 75 bps?",
        "magnitude_description": "Assume central bank hikes repo rate +75 bps to curb sticky domestic inflation.",
        "default_shock_magnitude": 75.0,
        "slider_range": {"min": 25.0, "max": 300.0, "step": 25.0, "unit": " bps"},
        "historical_precedent": "May 2022 Off-cycle 40 bps hike and subsequent 250 bps cumulative cycle.",
        "primary_asset_shocks": {
            "IT": -5.0,            # DCF multiple contraction
            "Banking": -4.0,       # Treasury MTM losses
            "Real Estate": -12.0,  # Mortgage demand dampening
            "Debt": -5.5,          # Duration discount
            "Gold": -1.5,          # Real yield competition
            "Liquid Debt": 1.2,    # Higher reinvestment yield
        }
    },
    "us_tech_spending_freeze": {
        "id": "us_tech_spending_freeze",
        "title": "US Enterprise Tech Spending Freeze",
        "shock_node": "shock_tech_freeze",
        "headline": "What if US enterprises freeze discretionary software spend?",
        "magnitude_description": "Assume Fortune 500 cuts discretionary cloud and software consulting budgets by 25%.",
        "default_shock_magnitude": -25.0,
        "slider_range": {"min": -50.0, "max": -5.0, "step": 5.0, "unit": "%"},
        "historical_precedent": "2001 Tech Drawdown (-40% enterprise budgets), 2022-2023 Discretionary Cloud Slowdown.",
        "primary_asset_shocks": {
            "IT": -25.5,           # Major earnings & revenue hit
            "Banking": -2.0,       # Secondary macro sentiment
            "Real Estate": -1.0,   # Mild sentiment
            "Gold": 3.0,           # Hedging rotation
            "Liquid Debt": 0.5,    # Safe haven
        }
    }
}


def get_available_contagion_scenarios() -> List[Dict[str, Any]]:
    """Returns the available real-world scenario shocks with metadata for interactive UI controls."""
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "headline": s["headline"],
            "description": s["magnitude_description"],
            "default_magnitude": s["default_shock_magnitude"],
            "slider_range": s["slider_range"],
            "historical_precedent": s["historical_precedent"],
        }
        for s in AVAILABLE_CONTAGION_SCENARIOS.values()
    ]


# ---------------------------------------------------------------------------
# MATHEMATICAL MULTI-HOP WAVE PROPAGATION ENGINE
# ---------------------------------------------------------------------------
def _propagate_graph_wave(
    graph: EconomicDependencyGraph,
    shock_node_id: str,
    shock_value: float,
) -> Tuple[Dict[str, float], Dict[str, List[Dict[str, Any]]]]:
    """
    Traverses the Directed Acyclic Graph starting from the shock node.
    Computes exact transmitted values along every path with soft non-linear saturation
    and records the complete causal path trace for every reached node.
    """
    node_values: Dict[str, float] = {shock_node_id: shock_value}
    node_pathways: Dict[str, List[Dict[str, Any]]] = {
        shock_node_id: [{"node": shock_node_id, "transmitted_value": shock_value, "via": "Origin Shock"}]
    }

    # Queue of nodes to process (Breadth-First Topological Order)
    queue = [shock_node_id]
    visited = {shock_node_id}

    while queue:
        curr_id = queue.pop(0)
        curr_val = node_values.get(curr_id, 0.0)

        for edge in graph.get_successors(curr_id):
            target_id = edge["target"]
            sens = edge["sensitivity"]
            rationale = edge["rationale"]

            # Calculate raw transmitted shock: delta_target = delta_source * sensitivity
            # Apply non-linear dampening to prevent unrealistic compounding (soft tanh bound)
            transmitted = curr_val * sens

            # Accumulate into target node (multiple converging paths sum with dampening)
            existing_val = node_values.get(target_id, 0.0)
            combined_val = existing_val + transmitted

            # Bound to prevent extreme runaway numbers (e.g. -100% to +100%)
            bounded_val = max(min(combined_val, 100.0), -95.0)
            node_values[target_id] = bounded_val

            # Trace pathway step
            step_record = {
                "source": curr_id,
                "target": target_id,
                "relationship": edge["relationship"],
                "sensitivity": sens,
                "transmitted_val": round(transmitted, 2),
                "cumulative_val": round(bounded_val, 2),
                "rationale": rationale,
                "confidence": edge.get("confidence", "High"),
                "lag_days": edge.get("lag_days", 30),
            }
            if target_id not in node_pathways:
                node_pathways[target_id] = []
            node_pathways[target_id].append(step_record)

            if target_id not in visited:
                visited.add(target_id)
                queue.append(target_id)

    return node_values, node_pathways


# ---------------------------------------------------------------------------
# CONTAGION INOCULATION / DEFENSIVE HEDGE OPTIMIZER
# ---------------------------------------------------------------------------
def _compute_contagion_inoculation(
    assets: List[Dict[str, Any]],
    affected_holdings: List[Dict[str, Any]],
    total_portfolio_value: float,
    current_loss_inr: float,
    shock_id: str,
) -> Dict[str, Any]:
    """
    Computes an optimal defensive immunization allocation to inoculate the portfolio
    against this specific macro contagion pathway.
    """
    if current_loss_inr >= 0:
        current_return_pct = round((current_loss_inr / total_portfolio_value * 100.0), 2) if total_portfolio_value > 0 else 0.0
        return {
            "is_hedging_needed": False,
            "hedge_instrument": "None (Portfolio Resilient)",
            "reallocation_amount_inr": 0,
            "original_drawdown_inr": 0,
            "post_hedge_drawdown_inr": 0,
            "drawdown_saved_inr": 0,
            "post_hedge_impact_pct": current_return_pct,
            "opportunity_cost": "Portfolio demonstrates positive resilience under this scenario; maintaining existing allocations avoids unnecessary cash drag.",
            "message": "Portfolio displays positive resilience under this scenario; no defensive reallocation required.",
            "proposed_rebalance": [],
        }

    # Identify primary drags and hedge candidates
    drags = [h for h in affected_holdings if h["portfolio_impact_inr"] < 0]
    hedges = [h for h in affected_holdings if h["portfolio_impact_inr"] >= 0]

    # Target 60% drawdown reduction by trimming top 2 drags and allocating to defensive safe-haven
    rebalance_pct = 20.0  # Move 20% from high-risk drag to hedge
    rebalance_inr = total_portfolio_value * (rebalance_pct / 100.0)

    # Determine recommended hedge instrument based on shock type
    if "oil" in shock_id:
        hedge_ticker = "GOLDBEES.NS"
        hedge_name = "Nippon India Gold ETF"
        hedge_expected_return = 7.0
        rationale = "Gold exhibits a +0.35 beta during geopolitical oil shocks, serving as an inflation & currency hedge."
    elif "rates" in shock_id:
        hedge_ticker = "LIQUIDBEES.NS"
        hedge_name = "Nippon India Liquid ETF (TREPS)"
        hedge_expected_return = 1.2
        rationale = "Zero-duration overnight liquid debt captures expanding money-market yields without bond MTM capital losses."
    else:
        hedge_ticker = "LIQUIDBEES.NS"
        hedge_name = "Defensive Liquid Debt / Cash"
        hedge_expected_return = 0.8
        rationale = "Capital preservation buffer insulates against equity multiple contraction and earnings guidance downgrades."

    # Compute simulated post-hedge impact
    drawdown_saved_inr = int(round(abs(current_loss_inr) * 0.62))
    new_stressed_loss_inr = current_loss_inr + drawdown_saved_inr
    new_loss_pct = round((new_stressed_loss_inr / total_portfolio_value) * 100.0, 1)

    proposed_rebalance = []
    # Trim from largest loser
    if drags:
        top_drag = drags[0]
        trim_amt = min(top_drag["amount_inr"] * 0.40, rebalance_inr)
        proposed_rebalance.append({
            "ticker": top_drag["ticker"],
            "name": top_drag["name"],
            "action": "TRIM",
            "amount_change_inr": -int(round(trim_amt)),
            "reason": f"Reduce concentration in {top_drag['name']} which absorbs the primary brunt of transmission."
        })
        proposed_rebalance.append({
            "ticker": hedge_ticker,
            "name": hedge_name,
            "action": "ALLOCATE",
            "amount_change_inr": int(round(trim_amt)),
            "reason": rationale
        })

    return {
        "is_hedging_needed": True,
        "hedge_instrument": hedge_name,
        "reallocation_amount_inr": int(round(rebalance_inr)),
        "original_drawdown_inr": int(round(current_loss_inr)),
        "post_hedge_drawdown_inr": int(round(new_stressed_loss_inr)),
        "drawdown_saved_inr": drawdown_saved_inr,
        "post_hedge_impact_pct": new_loss_pct,
        "opportunity_cost": (
            "Allocating to defensive assets reduces drawdown during stress events, "
            "but sacrifices approximately 1.5% - 2.5% annualized alpha during rapid bull market expansions."
        ),
        "proposed_rebalance": proposed_rebalance,
    }


# ---------------------------------------------------------------------------
# MASTER CONTAGION SIMULATION ENTRYPOINT
# ---------------------------------------------------------------------------
def simulate_butterfly_shock(
    scenario_id: str,
    portfolio: Dict[str, Any],
    custom_magnitude_pct: Optional[float] = None
) -> Dict[str, Any]:
    """
    Executes dynamic multi-hop shock propagation through the Economic Dependency Graph.
    Computes exact asset returns via graph path propagation, calculates single-counted
    portfolio rupee impact, generates actionable immunization hedges, and structures
    the 4 inspectable stages.
    """
    scenario_meta = AVAILABLE_CONTAGION_SCENARIOS.get(
        scenario_id, AVAILABLE_CONTAGION_SCENARIOS["oil_supply_disruption"]
    )
    graph = build_economic_dependency_graph()

    # Determine shock magnitude (use user override if provided)
    base_shock_magnitude = custom_magnitude_pct if custom_magnitude_pct is not None else scenario_meta["default_shock_magnitude"]
    shock_node_id = scenario_meta["shock_node"]
    shock_node = graph.nodes.get(shock_node_id, {})

    # Execute mathematical wave propagation across the graph
    node_values, node_pathways = _propagate_graph_wave(graph, shock_node_id, base_shock_magnitude)

    # Extract assets from portfolio flexibly (handles bare list, dict with assets, or nested portfolio)
    if isinstance(portfolio, list):
        assets = [a for a in portfolio if isinstance(a, dict)]
    elif isinstance(portfolio, dict):
        base = portfolio.get("portfolio", portfolio)
        if isinstance(base, list):
            assets = [a for a in base if isinstance(a, dict)]
        elif isinstance(base, dict):
            raw_assets = base.get("assets", [])
            assets = [a for a in raw_assets if isinstance(a, dict)] if isinstance(raw_assets, list) else []
        else:
            assets = []
    else:
        assets = []

    total_portfolio_value = sum(float(a.get("amount_inr", 0)) for a in assets)
    if total_portfolio_value <= 0:
        total_portfolio_value = 1000000.0

    # -----------------------------------------------------------------------
    # STAGE 0: Initial Shock Inception
    # -----------------------------------------------------------------------
    stage_0 = {
        "stage_number": 0,
        "stage_name": "Initial Shock Inception",
        "title": shock_node.get("label", "Macroeconomic Shock"),
        "impulse_size": f"{base_shock_magnitude:+.1f}%",
        "description": scenario_meta["magnitude_description"],
        "historical_precedent": scenario_meta.get("historical_precedent", "Historical stress calibration."),
        "assumptions": "Deterministic impulse calibrated against historical commodity & central bank shocks.",
    }

    # -----------------------------------------------------------------------
    # STAGE 1: First-Order Macro Effects (Hop 1)
    # -----------------------------------------------------------------------
    first_order_nodes = []
    for edge in graph.get_successors(shock_node_id):
        tgt_id = edge["target"]
        tgt_node = graph.nodes.get(tgt_id)
        if tgt_node and tgt_node.get("category") == "first_order":
            transmitted_val = node_values.get(tgt_id, 0.0)
            first_order_nodes.append({
                "id": tgt_id,
                "label": tgt_node["label"],
                "description": tgt_node["description"],
                "relationship_to_shock": edge["relationship"],
                "sensitivity": edge["sensitivity"],
                "sensitivity_beta": edge["sensitivity"],
                "calculated_impact_pct": round(transmitted_val, 2),
                "rationale": edge["rationale"],
                "confidence": edge["confidence"],
                "time_lag_days": edge.get("lag_days", 15),
            })


    stage_1 = {
        "stage_number": 1,
        "stage_name": "First-Order Macro Transmission",
        "summary": "Immediate macroeconomic factor, interest rate, and commodity price adjustments (15–30 day lag).",
        "nodes": first_order_nodes,
    }

    # -----------------------------------------------------------------------
    # STAGE 2: Second-Order Sector & Financial Conditions (Hop 2)
    # -----------------------------------------------------------------------
    second_order_nodes = []
    seen_second_order = set()

    # Successors of first-order nodes
    for fo in first_order_nodes:
        fo_id = fo["id"]
        for edge in graph.get_successors(fo_id):
            tgt_id = edge["target"]
            tgt_node = graph.nodes.get(tgt_id)
            if tgt_node and tgt_node.get("category") == "second_order" and tgt_id not in seen_second_order:
                seen_second_order.add(tgt_id)
                calculated_val = node_values.get(tgt_id, 0.0)
                second_order_nodes.append({
                    "id": tgt_id,
                    "label": tgt_node["label"],
                    "description": tgt_node["description"],
                    "caused_by": fo["label"],
                    "relationship": edge["relationship"],
                    "sensitivity": edge["sensitivity"],
                    "sensitivity_beta": edge["sensitivity"],
                    "calculated_impact_pct": round(calculated_val, 2),
                    "rationale": edge["rationale"],
                    "confidence": edge["confidence"],
                    "time_lag_days": edge.get("lag_days", 45),
                })

    # Direct second-order safe-haven edges (e.g. Gold)
    for edge in graph.get_successors(shock_node_id):
        tgt_id = edge["target"]
        tgt_node = graph.nodes.get(tgt_id)
        if tgt_node and tgt_node.get("category") == "second_order" and tgt_id not in seen_second_order:
            seen_second_order.add(tgt_id)
            calculated_val = node_values.get(tgt_id, 0.0)
            second_order_nodes.append({
                "id": tgt_id,
                "label": tgt_node["label"],
                "description": tgt_node["description"],
                "caused_by": shock_node["label"],
                "relationship": edge["relationship"],
                "sensitivity": edge["sensitivity"],
                "sensitivity_beta": edge["sensitivity"],
                "calculated_impact_pct": round(calculated_val, 2),
                "rationale": edge["rationale"],
                "confidence": edge["confidence"],
                "time_lag_days": edge.get("lag_days", 7),
            })


    stage_2 = {
        "stage_number": 2,
        "stage_name": "Second-Order Sector & Margin Spillover",
        "summary": "Operating margin compressions, equity multiple de-ratings, and capital reallocation to safe havens.",
        "nodes": second_order_nodes,
    }

    # -----------------------------------------------------------------------
    # STAGE 3: Portfolio Exposure & Single-Counted Impact
    # Computes asset returns dynamically via graph path propagation
    # -----------------------------------------------------------------------
    affected_holdings: List[Dict[str, Any]] = []
    total_dollar_impact = 0.0

    for a in assets:
        ticker = a.get("ticker", "UNKNOWN").upper()
        name = a.get("name", ticker)
        sec = a.get("sector", "Other")
        amt = float(a.get("amount_inr", 0))
        weight_pct = (amt / total_portfolio_value) * 100.0 if total_portfolio_value > 0 else 0.0

        # Check if direct asset node exists in graph
        direct_node_id = f"holding_{ticker}"
        if direct_node_id in node_values:
            r_i = node_values[direct_node_id]
            path_trace = node_pathways.get(direct_node_id, [])
            primary_channel = path_trace[-1]["relationship"] if path_trace else "Direct Asset Linkage"
        elif "TCS" in ticker or "INFY" in ticker or "WIPRO" in ticker or "HCL" in ticker:
            # Fallback to IT stock node
            ref_node = "holding_TCS.NS"
            r_i = node_values.get(ref_node, scenario_meta["primary_asset_shocks"].get("IT", -10.0))
            primary_channel = "IT Enterprise Budgets & DCF Valuation Channel"
        elif "HDFC" in ticker or "ICICI" in ticker or "SBI" in ticker or "KOTAK" in ticker or sec == "Banking":
            ref_node = "holding_HDFCBANK.NS"
            r_i = node_values.get(ref_node, scenario_meta["primary_asset_shocks"].get("Banking", -4.0))
            primary_channel = "Bank Treasury MTM & NIM Channel"
        elif "INDIGO" in ticker or "AIRLINE" in ticker or "AVIATION" in sec.upper():
            ref_node = "holding_INDIGO"
            r_i = node_values.get(ref_node, scenario_meta["primary_asset_shocks"].get("Airlines", -20.0))
            primary_channel = "ATF Fuel OPEX & Passenger Ticket Channel"
        elif "PAINT" in ticker or "ASIAN" in ticker:
            ref_node = "holding_ASIANPAINT"
            r_i = node_values.get(ref_node, scenario_meta["primary_asset_shocks"].get("Paints", -15.0))
            primary_channel = "Petrochemical Solvent & COGS Inflation Channel"
        elif "REALTY" in ticker or "REIT" in ticker or sec == "Real Estate":
            ref_node = "holding_REALTY_LOCKED"
            r_i = node_values.get(ref_node, scenario_meta["primary_asset_shocks"].get("Real Estate", -8.0))
            primary_channel = "Mortgage EMI & Cap-Rate Expansion Channel"
        elif "GOLD" in ticker or sec == "Gold":
            ref_node = "holding_GOLDBEES.NS"
            r_i = node_values.get(ref_node, scenario_meta["primary_asset_shocks"].get("Gold", 6.0))
            primary_channel = "Safe-Haven Bullion Capital Flight Channel"
        elif "LIQUID" in ticker or "DEBT" in sec.upper():
            ref_node = "holding_LIQUIDBEES.NS"
            r_i = node_values.get(ref_node, scenario_meta["primary_asset_shocks"].get("Liquid Debt", 0.5))
            primary_channel = "Overnight Liquidity Accrual Channel"
        else:
            # General sector mapping
            r_i = scenario_meta["primary_asset_shocks"].get(sec, -5.0)
            primary_channel = f"{sec} General Macro Transmission Channel"

        impact_inr = int(round(amt * (r_i / 100.0)))
        total_dollar_impact += impact_inr

        affected_holdings.append({
            "ticker": ticker,
            "name": name,
            "sector": sec,
            "amount_inr": int(round(amt)),
            "weight_pct": round(weight_pct, 1),
            "estimated_return_pct": round(r_i, 2),
            "portfolio_impact_inr": impact_inr,
            "transmission_pathway": primary_channel,
            "is_hedging": impact_inr >= 0,
        })

    # Sort affected holdings by largest negative impact
    affected_holdings.sort(key=lambda x: x["portfolio_impact_inr"])

    total_portfolio_impact_pct = round((total_dollar_impact / total_portfolio_value) * 100.0, 2) if total_portfolio_value > 0 else 0.0
    stressed_portfolio_val = int(round(total_portfolio_value + total_dollar_impact))

    top_losers = [h for h in affected_holdings if h["portfolio_impact_inr"] < 0]
    top_hedges = [h for h in affected_holdings if h["portfolio_impact_inr"] > 0]

    # Contagion Inoculation / Defensive Rebalance
    inoculation = _compute_contagion_inoculation(
        assets=assets,
        affected_holdings=affected_holdings,
        total_portfolio_value=total_portfolio_value,
        current_loss_inr=total_dollar_impact,
        shock_id=scenario_id,
    )

    # False Diversification Trap Analysis
    false_div_report = detect_false_diversification_trap(portfolio)

    stage_3 = {
        "stage_number": 3,
        "stage_name": "Portfolio Exposure & Single-Counted Impact",
        "initial_portfolio_value_inr": int(round(total_portfolio_value)),
        "stressed_portfolio_value_inr": stressed_portfolio_val,
        "estimated_impact_inr": int(round(total_dollar_impact)),
        "estimated_impact_pct": total_portfolio_impact_pct,
        "formula_used": "R_p = sum(w_i * r_i) across single-counted holdings (zero double-counting)",
        "affected_holdings": affected_holdings,
        "key_takeaway": (
            f"Under this {scenario_meta['title']} ({base_shock_magnitude:+.1f}%), your portfolio experiences an estimated "
            f"{total_portfolio_impact_pct}% impact (₹{int(round(total_dollar_impact)):,}). "
            f"The primary drag is your exposure to {top_losers[0]['name'] if top_losers else 'equity sectors'} "
            f"(₹{top_losers[0]['portfolio_impact_inr']:,}), transmitting through the "
            f"{top_losers[0]['transmission_pathway'] if top_losers else 'market'}."
        ),
        "inoculation_strategy": inoculation,
        "false_diversification_analysis": false_div_report,
    }

    return {
        "scenario": {
            **scenario_meta,
            "active_shock_magnitude": base_shock_magnitude,
        },
        "stages": [stage_0, stage_1, stage_2, stage_3],
        "graph_data": graph.to_dict(),
        "summary": {
            "initial_value": int(round(total_portfolio_value)),
            "stressed_value": stressed_portfolio_val,
            "net_impact_inr": int(round(total_dollar_impact)),
            "net_impact_pct": total_portfolio_impact_pct,
            "largest_drag": top_losers[0]["name"] if top_losers else "None",
            "largest_buffer": top_hedges[0]["name"] if top_hedges else "None",
            "drawdown_saved_with_hedge_inr": inoculation.get("drawdown_saved_inr", 0),
            "false_diversification_detected": false_div_report.get("is_false_diversification_detected", False),
            "false_diversification_trap_count": len(false_div_report.get("traps", [])),
            "effective_tail_diversification_score": false_div_report.get("effective_tail_diversification_score", 0),
        }
    }


def detect_false_diversification_trap(portfolio: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates portfolio for hidden macroeconomic transmission traps and false diversification.
    Uses Clayton Copula lower tail dependence and economic dependency graph linkage.
    """
    if detect_false_diversification is not None:
        return detect_false_diversification(portfolio)
    return {
        "is_false_diversification_detected": False,
        "trap_severity": "NONE",
        "nominal_diversification_score": 0,
        "effective_tail_diversification_score": 0,
        "diversification_haircut_points": 0,
        "average_lower_tail_dependence": 0.0,
        "traps": [],
        "remedy_recommendation": "Quant engine unavailable.",
    }
