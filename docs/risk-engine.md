# Risk Engine

## Portfolio representation

The F-06 API accepts an investor profile and a non-empty list of assets. An asset has ticker, name, sector, asset class, INR amount, liquidity tag, and currency exposure. The engine also accepts flexible internal payload shapes, but the public API validates the stricter Pydantic shape first.

## Composition and diversification

`compute_composition` sums INR amounts by sector and liquidity tag and expresses each as a percentage of total value. `compute_diversification_score` computes asset-weight HHI:

$$HHI = \sum_i w_i^2$$

It normalizes the result between the equal-weight and single-asset bounds, applies a penalty when one sector exceeds 50%, then clamps the displayed score to 5..95 for non-empty portfolios. A single asset returns 12. This is a heuristic score, not a regulated risk rating.

## Correlation

`build_correlation_matrix` first checks a hardcoded ticker-pair lookup. When no pair is found it infers a value from sectors: same-sector 0.82, IT/Banking 0.40, Debt involvement 0.10, Gold involvement -0.10, otherwise 0.35. The matrix is symmetric with diagonal 1.0. The first pair at or above 0.75 creates the high-correlation warning. This is not a runtime calculation from the CSV dataset.

## Scenario stress calculation

For each asset, `run_portfolio_scenario` combines:

- market effect: sector beta multiplied by market decline;
- sector effect: supplied sector shock;
- rate effect: negative sector duration multiplied by `interest_rate_change_bps / 100`;
- FX effect: for `USD_INR` or IT, `(-currency_shift) * 0.25`;
- transmission spillover: deterministic rate and low-liquidity freeze rules.

The stressed asset value is bounded below by zero. Portfolio impact is stressed value minus starting value. Sector defaults include betas, volatilities, and durations for IT, Banking, Real Estate, Gold, Debt, Liquid Debt, and others.

A positive rate shock adds IT DCF compression, Banking treasury markdown, or Real Estate mortgage drag. A market decline below -10% applies an additional low-liquidity haircut. These are modeled assumptions, not calibrated forecasts.

## Projection display

`compute_stochastic_cone_and_history` produces twelve fixed historical display months with hardcoded multipliers and six forward months. The projection median decays slightly, while P10/P90 are calculated with exponential volatility bands using approximately ±1.28 volatility units. A rebalanced median uses a separate positive decay. The implementation labels these outputs hypothetical and not guaranteed. The function does not currently read the CSV historical dataset.

## Alternative allocation

`generate_alternative_rebalance` always proposes 25% IT, 25% Banking, 20% Gold, and 30% Liquid Debt. It recalculates the stressed amount under the supplied scenario, reports a non-negative modeled drawdown difference, and uses a fixed 3.2% annual opportunity-cost assumption. The name contains “AI,” but the implementation is a deterministic heuristic and does not invoke an AI model.

## Additional metrics

The engine calculates:

- historical CVaR from the fixed display returns plus the scenario impact;
- pain index from the historical display values;
- ulcer index from drawdowns in those values;
- maximum drawdown display as `-abs(weighted_volatility * 1.25)`;
- tail dependence using a Clayton-style transformation of positive correlations;
- a false-diversification detector for high tail dependence, oil/petrochemical bottlenecks, and monetary tightening traps.

These metrics are model outputs. The fixed historical display series means they should not be described as independently measured live portfolio history.

## Reverse stress testing

`compute_reverse_stress_test` builds sector volatility and correlation matrices, clips the correlation matrix to positive semi-definite form, and forms:

$$\Sigma_{ij} = \sigma_i \sigma_j \rho_{ij}$$
$$\sigma_p^2 = w^T\Sigma w$$
$$\beta_p = \frac{\Sigma w}{\sigma_p^2}$$
$$S^* = -L\beta_p$$
$$D_M = \frac{L}{\sigma_p}$$

It then estimates a Gaussian lower-tail probability using `erfc`, ranks assets by portfolio beta, and returns a most-probable failure scenario. It is an analytical stress calculation, not a probability forecast validated against market observations.

## Contagion simulation

`contagion.py` builds a directed economic dependency graph of shocks, first-order factors, second-order effects, and assets. Each edge has sensitivity, rationale, confidence, and lag days. A breadth-first wave propagates shock values, sums converging paths, and bounds values between -95 and +100. The route returns staged causal effects, single-counted portfolio impact, and a hedge suggestion. NetworkX is optional; the module has a native dictionary fallback when NetworkX is unavailable.

## Parsing and guardrails

`parse_custom_scenario` uses lowercase keyword matching and regular expressions. It recognizes market decline language, rate bps, currency phrases, and sector keywords, with fixed bounds and a fallback preset. `generate_ai_insights` adds deterministic conflict rules for financial-trilemma CAGR, short horizon with high equity-sector weight, high liquidity need with illiquid share above 5%, low-risk drawdown below -12%, and correlation warnings.

No analysis output guarantees performance, detects every financial conflict, or replaces professional advice.
