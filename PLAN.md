# Comprehensive Approach & Technical Plan: Investment Portfolio Risk & Scenario Analysis
**Hackathon Problem Statement F-06 — Srujana 2026**
*Document Version: 1.0.0 | Location: `/PLAN.md` (Companion to `CONTRACT.md` and `README.md`)*

---

## 1. Executive Summary & Problem Framing

### 1.1 The Real-World Problem
Retail and semi-institutional investors in India often make allocation decisions in silos. They buy top-performing assets based on trailing returns without realizing:
1. **The "Illusion of Diversification":** Owning multiple stocks (e.g., TCS and Infosys) feels diversified, but both share a $0.88+$ correlation, identical dependency on US enterprise IT budgets, and direct sensitivity to INR/USD currency fluctuations.
2. **Hidden Macro Vulnerabilities:** A portfolio weighted in long-duration debt or real estate REITs may face unexpected capital destruction during an RBI repo rate tightening cycle (+75 to +150 bps), even if equities remain stable.
3. **Goal & Liquidity Conflicts:** Investors frequently allocate capital needed for short-term milestones (e.g., a home down payment in 12 months) into volatile equities or locked illiquid debt, creating severe liquidity traps during market downturns.
4. **Misleading Forecasts in FinTech:** Many consumer wealth apps present hypothetical return projections as deterministic linear forecasts, violating regulatory guardrails and giving users a false sense of security.

### 1.2 Our Solution Vision
An institutional-grade, transparent, and interactive portfolio stress-testing platform tailored for Indian market dynamics. Our platform allows investors to:
- Instantly diagnose asset concentration, hidden correlations, and liquidity profiles.
- Simulate dynamic multi-factor macro stress tests (Nifty index shocks, RBI rate hikes, sector crashes, and currency shifts) using interactive controls or natural language queries.
- Automatically identify personal goal, risk tolerance, and liquidity conflicts via rule-based and AI guardrails.
- Evaluate mathematically sound alternative rebalancing options with transparent trade-off analyses (e.g., drawdown protection vs. upside sacrifice).
- Rigorously differentiate historical facts from hypothetical stochastic projections (10th, 50th, and 90th percentile cones).

---

## 2. Core Architectural & Algorithmic Blueprint

```
                                  USER INTERFACE (Ahmad & Shyam)
    ┌────────────────────────────────────────────────────────────────────────────────────────┐
    │  - Portfolio Selector (Tech-Heavy, Rate-Sensitive, All-Weather)                        │
    │  - Interactive Macro Controls (Sliders & AI Prompt Box)                                │
    │  - Historical vs. Hypothetical Cone Chart (P10 / P50 / P90 + Rebalanced)               │
    │  - N×N Asset Correlation Heatmap & False Diversification Flags                         │
    │  - Goal Conflict Alerts (High/Medium Severity) & Side-by-Side Alternative Allocation   │
    └─────────────────────────────────────────▲──────────────────────────────────────────────┘
                                              │ REST (JSON)
                                              ▼
                               FASTAPI SERVER (Zama)
    ┌────────────────────────────────────────────────────────────────────────────────────────┐
    │  - Endpoint 1: GET  /api/portfolios          (Demo Portfolios & Investor Profiles)     │
    │  - Endpoint 2: POST /api/analyze-scenario   (Stress Test & Rebalance Engine)          │
    │  - CORS Middleware, Pydantic Schema Validation, In-Memory DB & Error Handling          │
    └─────────────────────────────▲────────────────────────────▲─────────────────────────────┘
                                  │                            │
             Internal Call 1      │                            │ Internal Call 2
             run_portfolio_scenario(...)                       │ generate_ai_insights(...)
                                  │                            │
                                  ▼                            ▼
                       QUANT ENGINE (Lead)             AI & RULES AGENT (Lead)
    ┌─────────────────────────────────────────┐  ┌───────────────────────────────────────────┐
    │ - Multi-Factor Macro Stress Model       │  │ - Natural Language to Shock Parser        │
    │ - HHI Concentration & Liquidity Weights │  │ - Goal & Liquidity Conflict Detector      │
    │ - Pearson Covariance & Correlation Grid │  │ - Transparent Assumption Generator        │
    │ - Stochastic Projection Cone (P10/50/90)│  │ - Trade-off & Opportunity Cost Synthesizer│
    │ - Heuristic Risk-Parity Rebalancer      │  │ - Mandatory Compliance Disclaimers        │
    └─────────────────────────────────────────┘  └───────────────────────────────────────────┘
```

---

## 3. Financial Engineering & Quant Methodology (`/backend/engine/quant.py`)

### 3.1 Concentration & Diversification Scoring
We quantify portfolio concentration using the normalized **Herfindahl-Hirschman Index (HHI)** across asset classes and individual holdings:
$$HHI = \sum_{i=1}^{N} w_i^2 \quad \text{where } w_i = \frac{\text{Amount}_i}{\text{Total Value}}$$
- Perfect diversification across $N$ equal assets: $HHI = 1/N$.
- Single-asset monopoly: $HHI = 1.0$.
- **Diversification Score (0 to 100):**
  $$\text{Score} = \max\left(0, \min\left(100, \text{round}\left(100 \times \left(1 - \frac{HHI - 1/N}{1 - 1/N}\right)\right)\right)\right)$$
  *(Penalized further if $\ge 60\%$ of total equity capital resides in a single sector).*

### 3.2 Multi-Factor Stress Testing Model
The stress response of each asset $i$ under a scenario shock vector $\vec{S}$ is computed via a multi-factor linear sensitivity model:
$$\Delta V_i = V_i \times \Big[ \beta_{m, i} \cdot \Delta M + \Delta S_{\text{sector}(i)} - (D_i \cdot \Delta R) + \gamma_{\text{fx}, i} \cdot \Delta FX \Big]$$

Where:
- $\Delta M$: Broad market shock (e.g., Nifty 50 decline, $-15\%$).
- $\beta_{m, i}$: Equity market beta (e.g., IT stocks $\beta \approx 1.15$, Banking $\beta \approx 1.25$, Gold $\beta \approx -0.10$, Cash/Liquid $\beta \approx 0.0$).
- $\Delta S_{\text{sector}(i)}$: Specific sector-level shock (e.g., IT spending freeze $-25\%$, Banking $-10\%$).
- $\Delta R$: Interest rate shift in basis points (converted to percentage: $\text{bps} / 10000$).
- $D_i$: Effective modified duration for debt/fixed-income assets ($D \approx 4.5$ years for long bonds, $D \approx 0.1$ for liquid debt, $D \approx 0.0$ for pure equities).
- $\gamma_{\text{fx}, i}$: Net currency exposure factor ($\gamma > 0$ for export-driven IT benefiting from USD appreciation; $\gamma < 0$ for import-heavy sectors).

Total Stressed Portfolio Value:
$$V_{\text{stressed}} = \sum_{i=1}^N (V_i + \Delta V_i)$$
$$\text{Estimated Impact (INR)} = V_{\text{stressed}} - V_{\text{initial}}, \quad \text{Impact (\%)} = \frac{\text{Estimated Impact}}{V_{\text{initial}}} \times 100$$

### 3.3 Correlation Matrix & False Diversification Flagging
We construct an $N \times N$ correlation matrix from historical asset returns:
$$\rho_{ij} = \frac{\text{Cov}(R_i, R_j)}{\sigma_i \sigma_j}$$
- **Automated Detection Rule:** Any off-diagonal pair $(i, j)$ with $\rho_{ij} > 0.75$ triggers a "False Diversification Alert" (e.g., TCS vs. Infosys at $0.88$). The system explicitly warns the user: *"Holding both assets does not provide genuine downside protection against sector shocks."*

### 3.4 Historical Observations vs. Hypothetical Stochastic Cone
To address Core Requirement #3 (*distinguish historical observations from hypothetical outcomes and avoid presenting uncertain projections as guaranteed results*):
- **Historical Observations (Past 12-24 Months):** Back-calculated actual portfolio trajectory from recorded NSE historical price data. Displayed as a continuous **solid line**.
- **Hypothetical Projection Cone (Forward 6-12 Months):** Forward paths simulated using Geometric Brownian Motion (GBM) with drift $\mu$ and volatility $\sigma$ conditioned on the stressed starting baseline:
  $$S_t = S_0 \exp\left( \left(\mu - \frac{1}{2}\sigma^2\right)t + \sigma \sqrt{t} Z \right)$$
  We extract the percentiles:
  - **$P_{10}$ (Worst-Case Path):** Severe prolonged downturn ($\approx -1.28\sigma$).
  - **$P_{50}$ (Median Expected Path):** Baseline recovery trajectory.
  - **$P_{90}$ (Best-Case Path):** Bullish rebound trajectory.
  - **Rebalanced $P_{50}$:** Median path of the alternative hedge portfolio.
- **Visual Presentation:** Rendered as a distinct **semi-transparent shaded confidence band** with an explicit disclaimer tag.

### 3.5 Rebalanced Alternative Allocation Generator
When high stress or conflicts are detected, the quant engine formulates a defensive alternative allocation using a disciplined heuristic:
1. **Cap Concentrated Sectors:** Limit any single sector to $\le 25\%$ of total portfolio value.
2. **Inject Uncorrelated Hedges:** Allocate $15\text{--}20\%$ to Gold (`GOLDBEES.NS`) and $20\text{--}30\%$ to Liquid Debt (`LIQUIDBEES.NS`).
3. **Liquidity Safeguard:** Ensure high-liquidity assets match or exceed the investor's stated liquidity requirement.
4. **Transparent Trade-off Calculation:**
   $$\text{Drawdown Saved (INR)} = V_{\text{alternative stressed}} - V_{\text{current stressed}}$$
   $$\text{Upside Forgone (\% p.a.)} = \mathbb{E}[R_{\text{current bull}}] - \mathbb{E}[R_{\text{alternative bull}}]$$

---

## 4. AI & Guardrail Agent Methodology (`/backend/engine/ai_agent.py`)

### 4.1 Natural Language Scenario Parsing
When users enter free-form stress prompts (e.g., *"What happens if US tech spending collapses by 20% and RBI hikes repo rates by 50 bps?"*), `parse_custom_scenario` translates the text into parametric shocks:
- Identifies macro keywords: "tech collapse" $\rightarrow$ IT sector: $-20\%$; "RBI hike 50 bps" $\rightarrow$ `interest_rate_change_bps = 50`.
- Bounds all parsed values within realistic financial guardrails (e.g., rate change between $-100$ and $+300$ bps, market drop between $-50\%$ and $0\%$) to prevent invalid inputs.

### 4.2 Deterministic Goal & Liquidity Conflict Detector
Before invoking the LLM, a deterministic rule engine evaluates the investor profile against portfolio characteristics:

| Conflict Rule | Condition | Severity | Triggered Message Example |
| :--- | :--- | :--- | :--- |
| **Horizon vs. Volatility** | `horizon_years <= 2` AND `equity_weight > 50%` | **HIGH** | *"Your investment horizon is only 1 year with Low risk tolerance, but 75% of your capital is in high-volatility equities."* |
| **Liquidity Mismatch** | `liquidity_need == 'High'` AND `illiquid_share_pct > 10%` | **HIGH / MEDIUM** | *"You marked Liquidity Need as High, but ₹1,00,000 (10%) is locked in low-liquidity real estate debt."* |
| **Risk Tolerance Breach** | `risk_tolerance == 'Low'` AND `stressed_loss_pct < -15%` | **HIGH** | *"Simulated loss of -20.5% exceeds your Low risk tolerance threshold (-10% max allowable drop)."* |
| **Asset Class Clustering** | `max_sector_weight > 50%` | **MEDIUM** | *"Severe sector concentration: 75% allocated to IT exposes portfolio to isolated tech industry shocks."* |

### 4.3 Transparent Assumption Logging
Every analysis explicitly details the underlying assumptions in the API response:
- Exact shock multipliers applied.
- Duration discount factor used for fixed income.
- Monte Carlo parameterization (number of simulation paths, historical lookback window).
- Explicit non-guarantee statement: *"Hypothetical projections are probabilistic simulations, not guaranteed future performance."*

---

## 5. Mock Data & Demonstration Portfolios (`/mock-data/portfolios.json`)

To provide immediate, impactful demos during judging, Zama's sandbox provides three pre-configured portfolios representing classic investor dilemmas:

1. **Portfolio 1: "Aggressive Tech Heavy" (The Hidden Trap)**
   - **Profile:** 1-Year Horizon, Low Risk Tolerance, High Liquidity Need, Target: ₹10,00,000.
   - **Assets:** TCS (40%), Infosys (35%), HDFC Bank (15%), Locked Real Estate REIT (10%).
   - **The Dilemma:** False diversification (TCS + INFY correlation = 0.88), extreme vulnerability to IT/USD downturns, and severe horizon/liquidity conflicts.
2. **Portfolio 2: "Conservative Retiree" (The Hidden Interest Rate Risk)**
   - **Profile:** 5-Year Horizon, Low Risk Tolerance, Medium Liquidity Need, Target: ₹25,00,000.
   - **Assets:** Long-Term Govt Gilts 10Y (50%), Corporate Bond Fund (30%), Real Estate REIT (15%), FMCG Equity (5%).
   - **The Dilemma:** Appears safe from stock crashes, but loses 8-12% capital value when RBI hikes interest rates by 100-150 bps due to bond duration.
3. **Portfolio 3: "All-Weather Balanced" (The Resilient Benchmark)**
   - **Profile:** 3-Year Horizon, Moderate Risk Tolerance, Medium Liquidity Need, Target: ₹15,00,000.
   - **Assets:** Nifty 50 ETF (35%), Short-Duration Debt/LiquidBees (30%), Gold ETF (20%), Banking/FMCG (15%).
   - **The Dilemma:** Shows strong resilience under stress testing with balanced drawdown and immediate liquidity.

---

## 6. Frontend User Experience & Visual Widgets (`/frontend/src/`)

### 6.1 User Flow Walkthrough
```
[1. Select Portfolio] ──► [2. Inspect Baseline Diagnostics]
                              ├── Asset & Sector Distribution
                              ├── Illiquid Share % & HHI Score
                              └── Correlation Heatmap (Alerting False Hedges)
                                        │
                                        ▼
                          [3. Configure Stress Test]
                              ├── Quick Preset (e.g., "IT Crash + RBI 75bps Hike")
                              ├── Fine-tune Macro Sliders (Market, Rates, USD/INR)
                              └── OR Type Natural Language Query
                                        │
                                        ▼
                          [4. Execute & Review Impact]
                              ├── Stressed Value & Impact % Metric Cards
                              ├── Goal Conflict Warning Badges (High/Medium)
                              └── Interactive Chart: Historical Line vs. Stochastic Cone
                                        │
                                        ▼
                          [5. Explore Alternative Rebalance]
                              ├── Side-by-Side Asset Table (Current vs. Proposed)
                              ├── Net Drawdown Saved vs. Opportunity Cost
                              └── One-Click "Apply Rebalance" to compare cones
```

### 6.2 Widget Isolation & Responsibility Matrix

| Teammate | Component / File | Purpose & Contract |
| :--- | :--- | :--- |
| **Ahmad** | `/frontend/src/App.tsx` & `/pages/Dashboard.tsx` | Main application shell, state management, API integration with Zama's endpoints, responsive grid layout. |
| **Shyam** | `<HistoricalVsHypotheticalChart />` | Recharts/Chart.js rendering historical data (solid line), stochastic projection cone (P10/P50/P90 shaded area), rebalanced P50 line, and mandatory disclaimer text. |
| **Shyam** | `<ScenarioControlPanel />` | Interactive UI with sliders for market drop, rate changes, currency shift, preset chips, and custom AI prompt box with run button. |
| **Shyam** | `<CorrelationHeatmap />` | $N \times N$ color-coded grid with tooltip explanations and prominent warning box for correlations $> 0.75$. |

---

## 7. Compliance, Guardrails & Evaluation Criteria Fulfillment

Our approach maps directly to every single requirement of Srujana Problem Statement F-06:

| Hackathon Requirement | How Our Approach Solves It | Technical Implementation |
| :--- | :--- | :--- |
| **1. Portfolio & Risk Factors** | Evaluates concentration, volatility, liquidity, duration, currency, and cross-asset correlations. | Quant HHI score, 3-year historical covariance matrix, duration-adjusted bond sensitivities. |
| **2. Scenario Simulation** | Simulates market crashes, RBI repo rate changes, sector disruptions, and INR/USD currency shifts. | Multi-factor linear/non-linear stress model with instant recalculation ($< 100\text{ ms}$). |
| **3. Decision Support & Alternative Allocations** | Compares current allocation with an AI-generated risk-adjusted alternative with clear trade-offs. | Heuristic risk parity rebalancer returning drawdown saved vs. upside opportunity cost. |
| **4. Explain Assumptions** | Full disclosure of all calculation parameters and factor shocks. | `ai_analysis.assumptions_used` string array returned and rendered in UI accordion. |
| **5. Goal & Liquidity Conflicts** | Detects mismatches between user horizon, risk appetite, liquidity needs, and holdings. | Deterministic rule engine flagging `HORIZON_VS_VOLATILITY`, `LIQUIDITY_MISMATCH`, etc. |
| **6. Distinguish Fact from Projection** | Prevents misleading linear return projections. | Distinct visual separation: solid historical line vs. shaded percentile uncertainty cone with disclaimers. |

---

## 8. Development Milestones & Verification Plan

```
[Phase 1: Contracts & Engine] ──► [Phase 2: API & Integration] ──► [Phase 3: Widgets & UI] ──► [Phase 4: Polish & Pitch]
```

### Phase 1: Core Quant & AI Engine (Lead Sandbox: `/backend/engine/`)
- Implement `run_portfolio_scenario` in `quant.py` with multi-factor formulas and percentile cone generation.
- Implement `generate_ai_insights` and `parse_custom_scenario` in `ai_agent.py` with deterministic conflict detection.
- Unit test with pytest: verify mathematical bounds, negative shock handling, and correlation matrix symmetry.

### Phase 2: FastAPI Server & Mock Data (Zama Sandbox: `/backend/`, `/mock-data/`)
- Populate `mock-data/portfolios.json` with the 3 realistic Indian portfolios.
- Implement `GET /api/portfolios` and `POST /api/analyze-scenario` in `main.py` matching `CONTRACT.md` schemas.
- Enable CORS, write automated test cases with `pytest` / `TestClient`.

### Phase 3: Frontend Shell & Isolated Widgets (Ahmad & Shyam Sandboxes)
- Ahmad configures Axios/Fetch client in `api/` and builds the responsive layout in `pages/Dashboard.tsx`.
- Shyam builds the 3 standalone widgets (`HistoricalVsHypotheticalChart`, `ScenarioControlPanel`, `CorrelationHeatmap`) in `components/widgets/`.
- Ahmad imports Shyam's widgets and binds them to live API state.

### Phase 4: End-to-End Testing & Hackathon Pitch Delivery
- End-to-end integration test: select Portfolio 1 $\rightarrow$ trigger "IT Sector Disruption" $\rightarrow$ verify chart updates, correlation warnings appear, and alternative portfolio table populates.
- Rehearse the 3-minute hackathon pitch:
  - **Minute 1: The Hook:** Show Portfolio 1. Explain how the investor thinks they are safe, but reveals 0.88 correlation and 1-year liquidity conflict.
  - **Minute 2: The Stress Lab:** Trigger the macro scenario slider. Watch portfolio drop by -20.5% on the stochastic cone chart.
  - **Minute 3: The Resolution:** Reveal the AI-assisted rebalanced portfolio (+₹1,45,000 drawdown saved), highlight the transparent trade-offs, and showcase the compliance disclaimers.

---

## 9. Summary for Collaborating Agents

> **Note for Parallel Agents:**
> This plan respects all boundaries established in `CONTRACT.md`. All teammates work strictly inside their designated directories to ensure zero git merge conflicts. Use the JSON schemas in `CONTRACT.md` as the single source of truth for all API contracts.
