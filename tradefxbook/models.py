"""
TradeFXBook Data Contracts and Validation Models.
Enforces strict schema validation, timestamp sanity, and analytical response structures.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class UserBase(BaseModel):
    id: str
    name: str
    email: str
    starting_balance: float = 50000.0
    currency: str = "USD"
    timezone: str = "UTC"
    is_demo: bool = True
    profile_description: Optional[str] = ""


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    created_at: str


class TradeBase(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=20)
    asset_class: str = Field(default="Forex")
    direction: str = Field(..., pattern="^(LONG|SHORT)$")
    status: str = Field(default="CLOSED", pattern="^(OPEN|CLOSED)$")
    is_demo: bool = True
    entry_time: str
    exit_time: Optional[str] = None
    entry_price: float = Field(..., gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    quantity: float = Field(..., gt=0)
    contract_size: float = Field(default=100000.0, gt=0)
    account_currency: str = Field(default="USD")
    stop_loss_price: Optional[float] = Field(default=None, gt=0)
    take_profit_price: Optional[float] = Field(default=None, gt=0)
    planned_risk_amount: Optional[float] = Field(default=None, ge=0)
    risk_pct_balance: Optional[float] = Field(default=None, ge=0)
    planned_rr_ratio: Optional[float] = Field(default=None, ge=0)
    strategy_or_setup: Optional[str] = Field(default="Discretionary")
    trading_session: Optional[str] = Field(default="London")
    tags: Optional[str] = ""
    notes: Optional[str] = ""
    emotional_state: Optional[str] = Field(default="Disciplined")
    plan_followed: bool = True
    mistakes_or_lessons: Optional[str] = ""
    commission: float = Field(default=0.0, ge=0)
    other_fees: float = Field(default=0.0, ge=0)
    signed_swap_adjustment: float = Field(default=0.0)

    @field_validator("entry_time")
    @classmethod
    def validate_entry_time(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            raise ValueError("entry_time must be a valid ISO 8601 timestamp string")
        return v

    @field_validator("exit_time")
    @classmethod
    def validate_exit_time(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                raise ValueError("exit_time must be a valid ISO 8601 timestamp string")
        return v

    @model_validator(mode="after")
    def validate_temporal_order_and_status(self) -> "TradeBase":
        if self.status == "CLOSED":
            if not self.exit_time:
                raise ValueError("exit_time is required when status is CLOSED")
            if self.exit_price is None or self.exit_price <= 0:
                raise ValueError("Valid positive exit_price is required when status is CLOSED")
            
            t_entry = datetime.fromisoformat(self.entry_time.replace("Z", "+00:00"))
            t_exit = datetime.fromisoformat(self.exit_time.replace("Z", "+00:00"))
            # Normalize naive/aware datetime comparison
            t_entry_utc = t_entry.astimezone() if t_entry.tzinfo else t_entry
            t_exit_utc = t_exit.astimezone() if t_exit.tzinfo else t_exit
            if t_entry.tzinfo is None and t_exit.tzinfo is not None:
                t_entry_utc = t_entry.replace(tzinfo=t_exit.tzinfo)
            elif t_entry.tzinfo is not None and t_exit.tzinfo is None:
                t_exit_utc = t_exit.replace(tzinfo=t_entry.tzinfo)
            if t_exit_utc < t_entry_utc:
                raise ValueError(f"exit_time ({self.exit_time}) must not precede entry_time ({self.entry_time})")
        return self


class TradeCreate(TradeBase):
    pass


class TradeUpdate(BaseModel):
    symbol: Optional[str] = None
    asset_class: Optional[str] = None
    direction: Optional[str] = Field(default=None, pattern="^(LONG|SHORT)$")
    status: Optional[str] = Field(default=None, pattern="^(OPEN|CLOSED)$")
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    entry_price: Optional[float] = Field(default=None, gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    quantity: Optional[float] = Field(default=None, gt=0)
    contract_size: Optional[float] = Field(default=None, gt=0)
    account_currency: Optional[str] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    planned_risk_amount: Optional[float] = None
    risk_pct_balance: Optional[float] = None
    planned_rr_ratio: Optional[float] = None
    strategy_or_setup: Optional[str] = None
    trading_session: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    emotional_state: Optional[str] = None
    plan_followed: Optional[bool] = None
    mistakes_or_lessons: Optional[str] = None
    commission: Optional[float] = Field(default=None, ge=0)
    other_fees: Optional[float] = Field(default=None, ge=0)
    signed_swap_adjustment: Optional[float] = None

    @field_validator("entry_time")
    @classmethod
    def validate_entry_time(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                raise ValueError("entry_time must be a valid ISO 8601 timestamp string")
        return v

    @field_validator("exit_time")
    @classmethod
    def validate_exit_time(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                raise ValueError("exit_time must be a valid ISO 8601 timestamp string")
        return v

    @model_validator(mode="after")
    def validate_update_temporal_order(self) -> "TradeUpdate":
        if self.entry_time and self.exit_time:
            t_entry = datetime.fromisoformat(self.entry_time.replace("Z", "+00:00"))
            t_exit = datetime.fromisoformat(self.exit_time.replace("Z", "+00:00"))
            if t_entry.tzinfo is None and t_exit.tzinfo is not None:
                t_entry = t_entry.replace(tzinfo=t_exit.tzinfo)
            elif t_entry.tzinfo is not None and t_exit.tzinfo is None:
                t_exit = t_exit.replace(tzinfo=t_entry.tzinfo)
            if t_exit < t_entry:
                raise ValueError(f"exit_time ({self.exit_time}) must not precede entry_time ({self.entry_time})")
        return self


class TradeOut(TradeBase):
    id: str
    user_id: str
    realized_r_multiple: Optional[float] = None
    gross_pnl: float
    net_pnl: float
    seed_batch: Optional[str] = None
    created_at: str
    updated_at: str


class PaginatedTrades(BaseModel):
    items: List[TradeOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class DailyPnLPoint(BaseModel):
    date: str  # YYYY-MM-DD in user timezone
    closed_trades_count: int
    gross_pnl: float
    commissions: float
    swap: float
    net_pnl: float
    cumulative_net_pnl: float
    is_winning_day: bool
    is_breakeven_day: bool


class EquityPoint(BaseModel):
    trade_id: Optional[str] = None
    timestamp: str
    realized_pnl: float
    equity: float
    high_water_mark: float
    drawdown_currency: float
    drawdown_pct: float


class ExtremeTrade(BaseModel):
    id: str
    symbol: str
    direction: str
    exit_time: str
    net_pnl: float
    r_multiple: Optional[float] = None


class ExtremeDay(BaseModel):
    date: str
    net_pnl: float
    trades_count: int


class BreakdownItem(BaseModel):
    key: str
    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate: Optional[float] = None
    net_pnl: float
    profit_factor: Optional[float] = None
    avg_trade_pnl: float


class PerformanceMetrics(BaseModel):
    user_id: str
    user_name: str
    account_currency: str
    starting_balance: float
    current_equity: float

    # Core 22 required metrics
    total_closed_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: Optional[float] = None  # wins / (wins + losses) * 100
    gross_profit: float
    gross_loss: float
    net_pnl: float
    profit_factor: Optional[float] = None
    expectancy: Optional[float] = None
    average_win: Optional[float] = None
    average_loss: Optional[float] = None
    average_rr_ratio: Optional[float] = None
    total_trading_costs: float
    average_holding_duration_seconds: Optional[float] = None
    best_trade: Optional[ExtremeTrade] = None
    worst_trade: Optional[ExtremeTrade] = None
    best_trading_day: Optional[ExtremeDay] = None
    worst_trading_day: Optional[ExtremeDay] = None
    realized_equity_curve_points: int
    max_drawdown_currency: float
    max_drawdown_pct: float

    # Secondary metrics
    average_daily_pnl: Optional[float] = None
    average_r_multiple: Optional[float] = None
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    profitable_days_count: int = 0
    losing_days_count: int = 0
    breakeven_days_count: int = 0
    total_calendar_days_in_period: int = 0


class DemoHealthReport(BaseModel):
    total_demo_users: int
    trades_per_user: Dict[str, int]
    total_seeded_trades: int
    total_closed_seeded_trades: int
    seed_batch: str
    is_healthy: bool
    checks: Dict[str, bool]
    timestamp: str
