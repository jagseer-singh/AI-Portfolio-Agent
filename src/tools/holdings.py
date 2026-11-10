"""
Portfolio holdings — mock brokerage data.

Simulates a brokerage API that returns the user's current portfolio positions.
Uses static data to avoid connecting to any live brokerage account.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from pydantic import BaseModel, Field

from src.tools.schemas import AssetClass


# --------------------------------------------------------------------------- #
#  Schemas
# --------------------------------------------------------------------------- #
class GetHoldingsRequest(BaseModel):
    """Request to fetch portfolio holdings. Optionally filter by asset class."""

    account_id: str = Field(
        default="default",
        description="Portfolio account identifier. Use 'default' for the main account.",
    )
    asset_class_filter: AssetClass | None = Field(
        default=None,
        description="Optional filter to return only holdings of a specific asset class.",
    )


class Holding(BaseModel):
    """A single portfolio position."""

    symbol: str
    asset_class: AssetClass
    quantity: float = Field(..., description="Number of shares/units held.")
    average_cost: float = Field(..., description="Average purchase price per unit.")
    purchase_date: str = Field(..., description="Date position was opened (YYYY-MM-DD).")


class HoldingsResponse(BaseModel):
    """Portfolio holdings result."""

    account_id: str
    holdings: list[Holding]
    total_positions: int
    as_of: str = Field(..., description="ISO-8601 timestamp of the snapshot.")


# --------------------------------------------------------------------------- #
#  Mock portfolio data
# --------------------------------------------------------------------------- #
MOCK_PORTFOLIOS: dict[str, list[dict]] = {
    "default": [
        # Equities — diversified tech + finance
        {
            "symbol": "AAPL",
            "asset_class": AssetClass.EQUITY,
            "quantity": 50,
            "average_cost": 150.00,
            "purchase_date": "2024-01-15",
        },
        {
            "symbol": "MSFT",
            "asset_class": AssetClass.EQUITY,
            "quantity": 30,
            "average_cost": 380.00,
            "purchase_date": "2024-03-20",
        },
        {
            "symbol": "GOOGL",
            "asset_class": AssetClass.EQUITY,
            "quantity": 40,
            "average_cost": 140.00,
            "purchase_date": "2024-02-10",
        },
        {
            "symbol": "NVDA",
            "asset_class": AssetClass.EQUITY,
            "quantity": 25,
            "average_cost": 95.00,
            "purchase_date": "2023-11-05",
        },
        {
            "symbol": "JPM",
            "asset_class": AssetClass.EQUITY,
            "quantity": 20,
            "average_cost": 170.00,
            "purchase_date": "2024-06-12",
        },
        # Bonds
        {
            "symbol": "TLT",
            "asset_class": AssetClass.BOND,
            "quantity": 100,
            "average_cost": 95.00,
            "purchase_date": "2024-04-01",
        },
        {
            "symbol": "BND",
            "asset_class": AssetClass.BOND,
            "quantity": 150,
            "average_cost": 73.50,
            "purchase_date": "2024-05-15",
        },
        # Gold
        {
            "symbol": "GLD",
            "asset_class": AssetClass.GOLD,
            "quantity": 45,
            "average_cost": 185.00,
            "purchase_date": "2024-01-20",
        },
        # Crypto
        {
            "symbol": "BTC-USD",
            "asset_class": AssetClass.CRYPTO,
            "quantity": 0.5,
            "average_cost": 42_000.00,
            "purchase_date": "2024-02-28",
        },
        {
            "symbol": "ETH-USD",
            "asset_class": AssetClass.CRYPTO,
            "quantity": 5.0,
            "average_cost": 2_800.00,
            "purchase_date": "2024-03-10",
        },
    ],
    "conservative": [
        {
            "symbol": "BND",
            "asset_class": AssetClass.BOND,
            "quantity": 500,
            "average_cost": 72.00,
            "purchase_date": "2023-06-01",
        },
        {
            "symbol": "AGG",
            "asset_class": AssetClass.BOND,
            "quantity": 300,
            "average_cost": 100.50,
            "purchase_date": "2023-07-15",
        },
        {
            "symbol": "GLD",
            "asset_class": AssetClass.GOLD,
            "quantity": 100,
            "average_cost": 175.00,
            "purchase_date": "2023-08-20",
        },
        {
            "symbol": "TLT",
            "asset_class": AssetClass.BOND,
            "quantity": 200,
            "average_cost": 98.00,
            "purchase_date": "2023-09-10",
        },
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
#  Tool implementation
# --------------------------------------------------------------------------- #
def execute_get_holdings(request: GetHoldingsRequest) -> HoldingsResponse:
    """Fetch portfolio holdings from mock data."""
    account_id = request.account_id.lower()
    if account_id not in MOCK_PORTFOLIOS:
        raise ValueError(
            f"Unknown account: {account_id}. "
            f"Available: {', '.join(MOCK_PORTFOLIOS.keys())}"
        )

    raw_holdings = MOCK_PORTFOLIOS[account_id]

    # Apply asset class filter if specified
    if request.asset_class_filter:
        raw_holdings = [
            h for h in raw_holdings if h["asset_class"] == request.asset_class_filter
        ]

    holdings = [Holding(**h) for h in raw_holdings]

    return HoldingsResponse(
        account_id=account_id,
        holdings=holdings,
        total_positions=len(holdings),
        as_of=_now_iso(),
    )
