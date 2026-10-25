from __future__ import annotations
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

# Support both `uvicorn backend.main:app` from the repository root and
# `uvicorn main:app` from inside the backend folder.
try:
    from .database import initialize_database, save_analysis
except ImportError:  # pragma: no cover - used when main.py is imported directly
    from database import initialize_database, save_analysis  # type: ignore[no-redef]

if __package__:
    from .journal.router import router as journal_router
    from .journal.storage import initialize_storage as initialize_journal_storage
else:  # pragma: no cover - supports running from inside backend/
    from journal.router import router as journal_router
    from journal.storage import initialize_storage as initialize_journal_storage

try:
    if __package__:
        from .engine.quant import run_portfolio_scenario, compute_reverse_stress_test
        from .engine.ai_agent import generate_ai_insights, parse_custom_scenario
        from .engine.contagion import simulate_butterfly_shock, get_available_contagion_scenarios
    else:  # pragma: no cover - supports running from inside backend/
        from engine.quant import run_portfolio_scenario, compute_reverse_stress_test
        from engine.ai_agent import generate_ai_insights, parse_custom_scenario
        from engine.contagion import simulate_butterfly_shock, get_available_contagion_scenarios
    _ENGINE_IMPORT_ERROR: str | None = None
except ImportError as exc:  # allow the API/docs to start before the lead's files exist
    run_portfolio_scenario = None  # type: ignore[assignment]
    compute_reverse_stress_test = None  # type: ignore[assignment]
    generate_ai_insights = None  # type: ignore[assignment]
    parse_custom_scenario = None  # type: ignore[assignment]
    simulate_butterfly_shock = None  # type: ignore[assignment]
    get_available_contagion_scenarios = None  # type: ignore[assignment]
    _ENGINE_IMPORT_ERROR = str(exc)


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("srujana_f06.api")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIOS_FILE = PROJECT_ROOT / "mock-data" / "portfolios.json"

RiskTolerance = Literal["Low", "Moderate", "High"]
LiquidityNeed = Literal["Low", "Medium", "High"]
LiquidityTag = Literal["Low", "Medium", "High"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InvestorProfile(StrictModel):
    horizon_years: float = Field(gt=0, le=100)
    risk_tolerance: RiskTolerance
    liquidity_need: LiquidityNeed
    target_goal_inr: float = Field(ge=0)


class Asset(StrictModel):
    ticker: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    sector: str = Field(min_length=1, max_length=80)
    asset_class: str = Field(min_length=1, max_length=60)
    amount_inr: float = Field(gt=0)
    liquidity_tag: LiquidityTag
    currency_exposure: str = Field(min_length=1, max_length=40)


class Scenario(StrictModel):
    preset_name: str = Field(default="Custom Scenario", min_length=1, max_length=120)
    market_decline_pct: float = Field(default=0.0, ge=-50.0, le=0.0)
    interest_rate_change_bps: int = Field(default=0, ge=-100, le=300)
    sector_shocks: dict[str, float] = Field(default_factory=dict)
    currency_inr_usd_shift_pct: float = Field(default=0.0, ge=-15.0, le=15.0)
    custom_ai_prompt: str = Field(default="", max_length=2000)

    @field_validator("sector_shocks")
    @classmethod
    def validate_sector_shocks(cls, values: dict[str, float]) -> dict[str, float]:
        cleaned: dict[str, float] = {}
        for sector, percentage in values.items():
            name = sector.strip()
            if not name:
                raise ValueError("sector shock keys cannot be empty")
            if not -60.0 <= percentage <= 60.0:
                raise ValueError(f"sector shock for {name} must be between -60 and +60 percent")
            cleaned[name] = percentage
        return cleaned


class DemoPortfolio(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    investor_profile: InvestorProfile
    assets: list[Asset] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_asset_tickers(self) -> "DemoPortfolio":
        tickers = [asset.ticker.upper() for asset in self.assets]
        if len(tickers) != len(set(tickers)):
            raise ValueError("each portfolio must contain unique ticker values")
        return self


class PortfolioFile(StrictModel):
    portfolios: list[DemoPortfolio] = Field(min_length=1)


class AnalysisRequest(StrictModel):
    # These two fields are optional metadata. The contract's core request only
    # requires investor_profile, assets and scenario.
    portfolio_id: str | None = None
    portfolio_name: str | None = None
    investor_profile: InvestorProfile
    assets: list[Asset] = Field(min_length=1)
    scenario: Scenario

    @model_validator(mode="after")
    def validate_unique_tickers(self) -> "AnalysisRequest":
        tickers = [asset.ticker.upper() for asset in self.assets]
        if len(tickers) != len(set(tickers)):
            raise ValueError("assets must have unique ticker values")
        return self


class ContagionSimulationRequest(BaseModel):
    scenario_id: str = Field(default="oil_supply_disruption")
    portfolio: dict[str, Any] | list[dict[str, Any]] | None = None
    assets: list[dict[str, Any]] | None = None
    custom_magnitude_pct: float | None = None

    model_config = ConfigDict(extra="ignore")


class ReverseStressTestRequest(BaseModel):
    portfolio: dict[str, Any] | list[dict[str, Any]] | None = None
    assets: list[dict[str, Any]] | None = None
    target_loss_pct: float = Field(default=15.0, gt=0.0, le=100.0)

    model_config = ConfigDict(extra="ignore")



@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    initialize_journal_storage()
    yield


app = FastAPI(
    title="Srujana F-06 Portfolio Risk API",
    description="Portfolio stress testing and scenario analysis prototype.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(journal_router)


def _get_cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok"}


@app.get("/api/portfolios")
def get_portfolios() -> dict[str, Any]:
    """Load and return the three demo portfolios from mock-data/portfolios.json."""
    if not PORTFOLIOS_FILE.is_file():
        logger.error("Portfolio JSON file not found: %s", PORTFOLIOS_FILE)
        raise HTTPException(
            status_code=500,
            detail="Demo portfolio data file is missing. Check mock-data/portfolios.json.",
        )

    try:
        with PORTFOLIOS_FILE.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)

        # Accept either {"portfolios": [...]} or a bare [...] in the file.
        if isinstance(raw_data, list):
            raw_data = {"portfolios": raw_data}

        data = PortfolioFile.model_validate(raw_data)
        return {"portfolios": [portfolio.model_dump() for portfolio in data.portfolios]}
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        logger.exception("Invalid portfolio data in %s", PORTFOLIOS_FILE)
        raise HTTPException(
            status_code=500,
            detail="Demo portfolio data is invalid. Check the JSON structure and required fields.",
        ) from exc
    except OSError as exc:
        logger.exception("Could not read portfolio data file")
        raise HTTPException(status_code=500, detail="Could not read demo portfolio data.") from exc


def _normalize_parser_shocks(parser_result: Any) -> dict[str, Any]:
    """Convert the lead's parser response into the quant engine's shock keys."""
    if not isinstance(parser_result, dict):
        raise ValueError("parse_custom_scenario() must return a dictionary")

    candidate: Any = parser_result.get(
        "parsed_shocks",
        parser_result.get("scenario_shocks", parser_result),
    )
    if not isinstance(candidate, dict):
        raise ValueError("parser result must contain a parsed_shocks dictionary")

    aliases = {
        "market_decline_pct": "market_drop_pct",
        "market_shock_pct": "market_drop_pct",
        "market_drop_pct": "market_drop_pct",
        "interest_rate_change_bps": "interest_rate_change_bps",
        "rate_change_bps": "interest_rate_change_bps",
        "currency_inr_usd_shift_pct": "currency_inr_usd_shift_pct",
        "currency_shift_pct": "currency_inr_usd_shift_pct",
        "sector_shocks": "sector_shocks",
    }
    normalized: dict[str, Any] = {}
    for key, value in candidate.items():
        target_key = aliases.get(key)
        if target_key is not None:
            normalized[target_key] = value

    if "sector_shocks" in normalized and not isinstance(normalized["sector_shocks"], dict):
        raise ValueError("parsed sector_shocks must be a dictionary")
    if not normalized:
        raise ValueError("parser did not return any recognized scenario shock fields")
    return normalized


def _make_scenario_shocks(scenario: Scenario) -> dict[str, Any]:
    """Translate API field names to the names expected by quant.py.

    Values parsed from a non-empty custom prompt override the corresponding
    slider values. Fields not mentioned in the prompt retain their slider values.
    """
    shocks: dict[str, Any] = {
        "market_drop_pct": scenario.market_decline_pct,
        "interest_rate_change_bps": scenario.interest_rate_change_bps,
        "sector_shocks": dict(scenario.sector_shocks),
        "currency_inr_usd_shift_pct": scenario.currency_inr_usd_shift_pct,
    }

    prompt = scenario.custom_ai_prompt.strip()
    if prompt:
        if parse_custom_scenario is None:
            logger.error("Scenario parser is unavailable. Import error: %s", _ENGINE_IMPORT_ERROR)
            raise HTTPException(status_code=503, detail="Scenario parser is not available yet.")
        try:
            parsed_result = parse_custom_scenario(prompt)
            parsed_shocks = _normalize_parser_shocks(parsed_result)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Custom scenario parsing failed")
            raise HTTPException(
                status_code=422,
                detail="Could not interpret the custom scenario. Try a clearer description or use the sliders.",
            ) from exc

        for key, value in parsed_shocks.items():
            if key == "sector_shocks":
                # Preserve manually configured sector shocks unless the prompt
                # specifies a shock for that same sector.
                shocks["sector_shocks"].update(value)
            else:
                shocks[key] = value

    return shocks


def _build_composition(assets: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate sector and liquidity composition directly from supplied holdings."""
    total_value = sum(float(asset["amount_inr"]) for asset in assets)
    if total_value <= 0:
        raise HTTPException(status_code=422, detail="Total portfolio value must be positive.")

    sector_values: dict[str, float] = {}
    liquidity_values = {"High": 0.0, "Medium": 0.0, "Low": 0.0}
    for asset in assets:
        amount = float(asset["amount_inr"])
        sector = str(asset["sector"])
        liquidity = str(asset["liquidity_tag"])
        sector_values[sector] = sector_values.get(sector, 0.0) + amount
        liquidity_values[liquidity] = liquidity_values.get(liquidity, 0.0) + amount

    by_sector = [
        {"sector": sector, "weight_pct": round(value / total_value * 100.0, 4)}
        for sector, value in sorted(sector_values.items(), key=lambda pair: pair[1], reverse=True)
    ]
    by_liquidity = {
        tag: round(value / total_value * 100.0, 4)
        for tag, value in liquidity_values.items()
    }
    return {"by_sector": by_sector, "by_liquidity": by_liquidity}


def _required_metric(metrics: dict[str, Any], key: str, *aliases: str) -> Any:
    for candidate in (key, *aliases):
        if candidate in metrics and metrics[candidate] is not None:
            return metrics[candidate]
    raise HTTPException(
        status_code=502,
        detail=f"Quant engine result is missing required risk metric '{key}'. Check the shared engine contract.",
    )


def _normalize_correlation_matrix(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise HTTPException(status_code=502, detail="Quant engine did not return a correlation_matrix object.")

    tickers = raw.get("tickers")
    matrix = raw.get("matrix")
    if not isinstance(tickers, list) or not isinstance(matrix, list):
        raise HTTPException(status_code=502, detail="correlation_matrix must contain 'tickers' and 'matrix'.")
    if len(matrix) != len(tickers) or any(not isinstance(row, list) or len(row) != len(tickers) for row in matrix):
        raise HTTPException(status_code=502, detail="The correlation matrix dimensions do not match the ticker list.")

    warning = raw.get("high_correlation_warning")
    if not warning:
        warnings: list[str] = []
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                try:
                    correlation = float(matrix[i][j])
                except (TypeError, ValueError):
                    continue
                if correlation > 0.75:
                    warnings.append(
                        f"{tickers[i]} and {tickers[j]} have correlation {correlation:.2f}; "
                        "these holdings may provide limited diversification during shared risk events."
                    )
        warning = " ".join(warnings) if warnings else None

    return {"tickers": tickers, "matrix": matrix, "high_correlation_warning": warning}


def _normalize_historical_series(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        raise HTTPException(status_code=502, detail="Quant engine did not return historical_series.")
    if not isinstance(raw, list):
        raise HTTPException(status_code=502, detail="historical_series must be a list.")

    normalized: list[dict[str, Any]] = []
    for point in raw:
        if not isinstance(point, dict):
            raise HTTPException(status_code=502, detail="Each historical_series point must be an object.")
        month = point.get("month", point.get("date", point.get("timestamp")))
        value = point.get("actual_value", point.get("portfolio_value_inr", point.get("value")))
        if month is None or value is None:
            raise HTTPException(
                status_code=502,
                detail="Each historical point must contain a date/month and an actual portfolio value.",
            )
        normalized.append({"month": str(month), "actual_value": value})
    return normalized


def _normalize_projection_cone(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        raise HTTPException(status_code=502, detail="Quant engine did not return hypothetical_cone.")
    if not isinstance(raw, list):
        raise HTTPException(status_code=502, detail="hypothetical_cone must be a list.")

    normalized: list[dict[str, Any]] = []
    for point in raw:
        if not isinstance(point, dict):
            raise HTTPException(status_code=502, detail="Each hypothetical_cone point must be an object.")
        month = point.get("month", point.get("date", point.get("timestamp")))
        p10 = point.get("p10_worst_case", point.get("p10"))
        p50 = point.get("p50_median_case", point.get("p50"))
        p90 = point.get("p90_best_case", point.get("p90"))
        rebalanced_p50 = point.get("rebalanced_p50", point.get("rebalanced_median"))
        if month is None or p10 is None or p50 is None or p90 is None:
            raise HTTPException(
                status_code=502,
                detail="Each projection point must contain month/date and P10, P50 and P90 values.",
            )
        normalized.append(
            {
                "month": str(month),
                "p10_worst_case": p10,
                "p50_median_case": p50,
                "p90_best_case": p90,
                # None means the engine did not provide this series; no value is fabricated.
                "rebalanced_p50": rebalanced_p50,
            }
        )
    return normalized


def _build_response(
    *,
    portfolio: dict[str, Any],
    quant_results: dict[str, Any],
    ai_results: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(quant_results, dict):
        raise HTTPException(status_code=502, detail="Quant engine must return a dictionary.")
    if not isinstance(ai_results, dict):
        raise HTTPException(status_code=502, detail="AI insights function must return a dictionary.")

    metrics = quant_results.get("risk_metrics")
    if not isinstance(metrics, dict):
        raise HTTPException(status_code=502, detail="Quant engine result is missing its risk_metrics object.")

    summary = {
        "total_value_inr": _required_metric(metrics, "total_value_inr"),
        "stressed_value_median_inr": _required_metric(metrics, "stressed_value_median_inr"),
        "estimated_impact_inr": _required_metric(metrics, "estimated_impact_inr"),
        "estimated_impact_pct": _required_metric(metrics, "estimated_impact_pct"),
        "annualized_volatility_pct": _required_metric(metrics, "annualized_volatility_pct", "volatility_pct"),
        "max_drawdown_pct": _required_metric(metrics, "max_drawdown_pct"),
        "diversification_score_out_of_100": _required_metric(
            metrics, "diversification_score_out_of_100", "diversification_score"
        ),
        "illiquid_ share_pct": _required_metric(metrics, "illiquid_ share_pct", "illiquid_share_pct"),
        "illiquid_share_pct": _required_metric(metrics, "illiquid_share_pct", "illiquid_ share_pct"),
    }

    if "cvar_95_pct" in metrics:
        summary["cvar_95_pct"] = metrics["cvar_95_pct"]
    if "pain_index" in metrics:
        summary["pain_index"] = metrics["pain_index"]
    if "ulcer_index" in metrics:
        summary["ulcer_index"] = metrics["ulcer_index"]

    correlation_matrix = _normalize_correlation_matrix(quant_results.get("correlation_matrix"))
    historical = _normalize_historical_series(quant_results.get("historical_series"))
    projection = _normalize_projection_cone(quant_results.get("hypothetical_cone"))

    assumptions = ai_results.get("assumptions_list", ai_results.get("assumptions_used", []))
    goal_conflicts = ai_results.get("goal_conflicts", [])
    if not isinstance(assumptions, list) or not isinstance(goal_conflicts, list):
        raise HTTPException(status_code=502, detail="AI results must contain list fields for assumptions and goal_conflicts.")

    quant_alternative = quant_results.get("alternative_portfolio")
    ai_alternative = ai_results.get("alternative_portfolio", {})
    if quant_alternative is None:
        quant_alternative = {}
    if ai_alternative is None:
        ai_alternative = {}
    if not isinstance(quant_alternative, dict) or not isinstance(ai_alternative, dict):
        raise HTTPException(status_code=502, detail="alternative_portfolio must be an object.")
    alternative = {**quant_alternative, **ai_alternative}

    tradeoff = ai_results.get("tradeoff_summary")
    if tradeoff is not None and "tradeoff_explanation" not in alternative:
        alternative["tradeoff_explanation"] = tradeoff

    if not alternative:
        raise HTTPException(status_code=502, detail="Neither engine returned alternative_portfolio.")

    return {
        "summary": summary,
        "composition": _build_composition(portfolio["assets"]),
        "correlation_matrix": correlation_matrix,
        "chart_data": {
            "disclaimer": (
                "Historical observations reflect the historical dataset supplied to this analysis. "
                "Hypothetical projections are model-based scenarios, not guaranteed future results."
            ),
            "historical_observations": historical,
            "hypothetical_projection_cone": projection,
        },
        "ai_analysis": {
            "assumptions_used": assumptions,
            "goal_conflicts": goal_conflicts,
            "alternative_portfolio": alternative,
        },
    }


@app.post("/api/analyze-scenario")
def analyze_scenario(request: AnalysisRequest) -> dict[str, Any]:
    """Run risk analysis and return the API response specified in CONTRACT.md."""
    if run_portfolio_scenario is None or generate_ai_insights is None:
        logger.error("Analysis engine is unavailable. Import error: %s", _ENGINE_IMPORT_ERROR)
        raise HTTPException(
            status_code=503,
            detail="The quantitative/AI engine is not available. Confirm backend/engine files and imports with the project lead.",
        )

    portfolio = {
        "investor_profile": request.investor_profile.model_dump(),
        "assets": [asset.model_dump() for asset in request.assets],
    }
    scenario_shocks = _make_scenario_shocks(request.scenario)

    try:
        quant_results = run_portfolio_scenario(portfolio, scenario_shocks)
        ai_results = generate_ai_insights(
            portfolio,
            quant_results,
            request.scenario.custom_ai_prompt.strip(),
        )
        response = _build_response(
            portfolio=portfolio,
            quant_results=quant_results,
            ai_results=ai_results,
        )
        record_id = save_analysis(
            portfolio_id=request.portfolio_id,
            portfolio_name=request.portfolio_name or request.portfolio_id or "Custom Portfolio",
            scenario={
                **scenario_shocks,
                "preset_name": request.scenario.preset_name,
                "custom_ai_prompt": request.scenario.custom_ai_prompt,
            },
            result=response,
        )
        logger.info("Analysis completed and saved. Internal analysis ID: %s", record_id)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Scenario analysis failed")
        raise HTTPException(
            status_code=502,
            detail="Scenario analysis failed. Check server logs and confirm the engine output matches CONTRACT.md.",
        ) from exc


@app.get("/api/contagion/scenarios")
def get_contagion_scenarios() -> dict[str, Any]:
    """Return available real-world shock scenarios for the Butterfly Effect simulator."""
    if get_available_contagion_scenarios is None:
        raise HTTPException(status_code=503, detail="Contagion engine is not available yet.")
    return {"scenarios": get_available_contagion_scenarios()}


@app.post("/api/contagion/simulate")
def simulate_contagion(request: ContagionSimulationRequest) -> dict[str, Any]:
    """Simulate multi-hop butterfly contagion across the economic dependency graph."""
    if simulate_butterfly_shock is None:
        raise HTTPException(status_code=503, detail="Contagion engine is not available yet.")
    try:
        portfolio_data: Any = None
        if request.assets is not None:
            portfolio_data = {"assets": request.assets}
        elif request.portfolio is not None:
            if isinstance(request.portfolio, list):
                portfolio_data = {"assets": request.portfolio}
            elif isinstance(request.portfolio, dict):
                portfolio_data = request.portfolio

        # Only fall back to mock data if neither assets nor portfolio were provided in request
        if portfolio_data is None:
            if PORTFOLIOS_FILE.is_file():
                with PORTFOLIOS_FILE.open("r", encoding="utf-8") as file:
                    raw_data = json.load(file)
                    portfolios = raw_data if isinstance(raw_data, list) else raw_data.get("portfolios", [])
                    if portfolios:
                        portfolio_data = portfolios[0]
            if portfolio_data is None:
                portfolio_data = {"assets": []}

        result = simulate_butterfly_shock(
            scenario_id=request.scenario_id,
            portfolio=portfolio_data,
            custom_magnitude_pct=request.custom_magnitude_pct,
        )

        # Mirror false diversification metrics at root level for frontend UI convenience
        fda = {}
        for stage in result.get("stages", []):
            if "false_diversification_analysis" in stage:
                fda = stage["false_diversification_analysis"]
                break

        is_fda = fda.get("is_false_diversification_detected", False)
        result["is_false_diversification_detected"] = is_fda
        result["nominal_diversification_score"] = fda.get("nominal_diversification_score")
        result["effective_tail_diversification_score"] = fda.get("effective_tail_diversification_score")
        result["diversification_haircut_points"] = fda.get("diversification_haircut_points")
        if is_fda and fda.get("traps"):
            result["upstream_dependency"] = (
                fda["traps"][0].get("upstream_bottleneck")
                or fda["traps"][0].get("common_vulnerability")
                or fda["traps"][0].get("name")
            )
        elif is_fda:
            result["upstream_dependency"] = "Upstream Commodity / Factor Concentration"
        else:
            result["upstream_dependency"] = None

        return result
    except Exception as exc:
        logger.exception("Butterfly contagion simulation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/reverse-stress-test")
def reverse_stress_test(request: ReverseStressTestRequest) -> dict[str, Any]:
    """
    Reverse Stress Testing (RST) Engine:
    Solves the analytical Most Probable Failure Scenario (MPFS) that causes target portfolio loss L.
    Computes Mahalanobis distance in sigmas and asset fragility rankings.
    """
    if compute_reverse_stress_test is None:
        raise HTTPException(status_code=503, detail="Quant engine is not available yet.")

    try:
        portfolio_data: Any = None
        if request.assets is not None:
            portfolio_data = {"assets": request.assets}
        elif request.portfolio is not None:
            if isinstance(request.portfolio, list):
                portfolio_data = {"assets": request.portfolio}
            elif isinstance(request.portfolio, dict):
                portfolio_data = request.portfolio

        # Only fall back to mock data if neither assets nor portfolio were provided in request
        if portfolio_data is None:
            if PORTFOLIOS_FILE.is_file():
                with PORTFOLIOS_FILE.open("r", encoding="utf-8") as file:
                    raw_data = json.load(file)
                    portfolios = raw_data if isinstance(raw_data, list) else raw_data.get("portfolios", [])
                    if portfolios:
                        portfolio_data = portfolios[0]
            if portfolio_data is None:
                portfolio_data = {"assets": []}

        result = compute_reverse_stress_test(
            portfolio=portfolio_data,
            target_loss_pct=request.target_loss_pct,
        )
        return result
    except Exception as exc:
        logger.exception("Reverse stress test execution failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/butterfly", response_class=HTMLResponse)
def get_butterfly_visualizer() -> str:
    """Serve the interactive standalone Butterfly Effect Contagion visualizer."""
    vis_path = Path(__file__).resolve().parent / "engine" / "contagion_visualizer.html"
    if not vis_path.is_file():
        raise HTTPException(status_code=404, detail="Visualizer HTML file not found.")
    return vis_path.read_text(encoding="utf-8")


