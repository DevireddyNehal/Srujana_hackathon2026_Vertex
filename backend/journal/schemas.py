from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TradeSide = Literal["long", "short"]
TradeStatus = Literal["open", "closed"]


class JournalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TradeCreate(JournalModel):
    symbol: str = Field(min_length=1, max_length=24)
    side: TradeSide
    quantity: float = Field(gt=0, le=1_000_000_000)
    entry_price: float = Field(gt=0, le=1_000_000_000)
    exit_price: float | None = Field(default=None, gt=0, le=1_000_000_000)
    opened_at: datetime
    closed_at: datetime | None = None
    fees: float = Field(default=0, ge=0, le=1_000_000_000)
    stop_loss: float | None = Field(default=None, gt=0, le=1_000_000_000)
    strategy: str = Field(default="", max_length=80)
    setup: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("opened_at", "closed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must include a timezone")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        cleaned = [tag.strip() for tag in values]
        if any(not tag or len(tag) > 40 for tag in cleaned):
            raise ValueError("tags must be between 1 and 40 characters")
        if len({tag.casefold() for tag in cleaned}) != len(cleaned):
            raise ValueError("tags must be unique")
        return cleaned

    @model_validator(mode="after")
    def validate_trade_timing(self) -> TradeCreate:
        if (self.exit_price is None) != (self.closed_at is None):
            raise ValueError("exit_price and closed_at must either both be set or both be empty")
        if self.closed_at is not None and self.closed_at <= self.opened_at:
            raise ValueError("closed_at must be later than opened_at")
        if self.stop_loss is not None:
            if self.side == "long" and self.stop_loss >= self.entry_price:
                raise ValueError("a long trade stop_loss must be below entry_price")
            if self.side == "short" and self.stop_loss <= self.entry_price:
                raise ValueError("a short trade stop_loss must be above entry_price")
        return self


class TradeUpdate(JournalModel):
    symbol: str | None = Field(default=None, min_length=1, max_length=24)
    side: TradeSide | None = None
    quantity: float | None = Field(default=None, gt=0, le=1_000_000_000)
    entry_price: float | None = Field(default=None, gt=0, le=1_000_000_000)
    exit_price: float | None = Field(default=None, gt=0, le=1_000_000_000)
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    fees: float | None = Field(default=None, ge=0, le=1_000_000_000)
    stop_loss: float | None = Field(default=None, gt=0, le=1_000_000_000)
    strategy: str | None = Field(default=None, max_length=80)
    setup: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("opened_at", "closed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_complete_trade(self) -> TradeUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        nullable_fields = {"exit_price", "closed_at", "stop_loss"}
        for field_name in self.model_fields_set - nullable_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.tags is not None:
            cleaned = [tag.strip() for tag in self.tags]
            if any(not tag or len(tag) > 40 for tag in cleaned):
                raise ValueError("tags must be between 1 and 40 characters")
            if len({tag.casefold() for tag in cleaned}) != len(cleaned):
                raise ValueError("tags must be unique")
            self.tags = cleaned
        return self
