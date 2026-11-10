"""
Portfolio valuation engine.

Chains the holdings-fetch tool into the price-fetch tool to compute
current portfolio value, gains/losses, and allocation breakdowns.

This is a "compute" tool — it orchestrates other tools internally
rather than requiring the LLM to chain them manually.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from src.tools.schemas import AssetClass
from src.tools.holdings import (
    GetHoldingsRequest,
    Holding,
    execute_get_holdings,
)
from src.tools.mock_data import (
    execute_get_asset_price,
    MOCK_PRICES,
)
from src.tools.schemas import GetAssetPriceRequest


# --------------------------------------------------------------------------- #
#  Schemas
# --------------------------------------------------------------------------- #
class GetPortfolioValuationRequest(BaseModel):
    """Request to compute current portfolio valuation."""

    account_id: str = Field(
        default="default",
        description="Portfolio account identifier.",
    )
    include_breakdown: bool = Field(
        default=True,
        description="Whether to include per-position and per-class breakdowns.",
    )


class PositionValuation(BaseModel):
    """Valuation of a single position."""

    symbol: str
    asset_class: AssetClass
    quantity: float
    average_cost: float
    current_price: float
    cost_basis: float = Field(..., description="quantity × average_cost")
    market_value: float = Field(..., description="quantity × current_price")
    unrealized_pnl: float = Field(..., description="market_value − cost_basis")
    unrealized_pnl_pct: float = Field(..., description="PnL as percentage of cost basis")
    weight_pct: float = Field(
        default=0.0, description="Position weight as % of total portfolio"
    )


class AssetClassBreakdown(BaseModel):
    """Aggregated valuation by asset class."""

    asset_class: AssetClass
    total_cost_basis: float
    total_market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight_pct: float = Field(..., description="Asset class weight as % of total portfolio")
    position_count: int


class PortfolioValuationResponse(BaseModel):
    """Full portfolio valuation result."""

    account_id: str
    total_cost_basis: float
    total_market_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    positions: list[PositionValuation] = Field(default_factory=list)
    asset_class_breakdown: list[AssetClassBreakdown] = Field(default_factory=list)
    timestamp: str
    currency: str = "USD"


# --------------------------------------------------------------------------- #
#  Valuation logic — chains holdings → prices → calculations
# --------------------------------------------------------------------------- #
def execute_portfolio_valuation(
    request: GetPortfolioValuationRequest,
) -> PortfolioValuationResponse:
    """
    Chain: fetch holdings → fetch current prices → compute valuation.

    This demonstrates the multi-tool chaining pattern:
    1. Call get_holdings to retrieve positions
    2. For each position, call get_asset_price to get current price
    3. Compute cost basis, market value, PnL, and allocation weights
    """
    # Step 1: Fetch holdings
    holdings_req = GetHoldingsRequest(account_id=request.account_id)
    holdings_resp = execute_get_holdings(holdings_req)

    # Step 2: Fetch prices and compute per-position valuations
    positions: list[PositionValuation] = []
    total_cost = 0.0
    total_value = 0.0

    for holding in holdings_resp.holdings:
        # Chain into price tool
        try:
            price_req = GetAssetPriceRequest(
                symbol=holding.symbol,
                asset_class=holding.asset_class,
            )
            price_resp = execute_get_asset_price(price_req)
            current_price = price_resp.price
        except ValueError:
            # Price not available — use average cost as fallback
            current_price = holding.average_cost

        cost_basis = holding.quantity * holding.average_cost
        market_value = holding.quantity * current_price
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis != 0 else 0.0

        total_cost += cost_basis
        total_value += market_value

        positions.append(
            PositionValuation(
                symbol=holding.symbol,
                asset_class=holding.asset_class,
                quantity=holding.quantity,
                average_cost=holding.average_cost,
                current_price=current_price,
                cost_basis=round(cost_basis, 2),
                market_value=round(market_value, 2),
                unrealized_pnl=round(pnl, 2),
                unrealized_pnl_pct=round(pnl_pct, 2),
            )
        )

    # Step 3: Compute weights
    for pos in positions:
        pos.weight_pct = round((pos.market_value / total_value * 100) if total_value else 0, 2)

    # Step 4: Asset class breakdown
    class_groups: dict[AssetClass, list[PositionValuation]] = {}
    for pos in positions:
        class_groups.setdefault(pos.asset_class, []).append(pos)

    breakdowns: list[AssetClassBreakdown] = []
    for ac, group in sorted(class_groups.items(), key=lambda x: x[0].value):
        class_cost = sum(p.cost_basis for p in group)
        class_value = sum(p.market_value for p in group)
        class_pnl = class_value - class_cost
        breakdowns.append(
            AssetClassBreakdown(
                asset_class=ac,
                total_cost_basis=round(class_cost, 2),
                total_market_value=round(class_value, 2),
                unrealized_pnl=round(class_pnl, 2),
                unrealized_pnl_pct=round(
                    (class_pnl / class_cost * 100) if class_cost else 0, 2
                ),
                weight_pct=round(
                    (class_value / total_value * 100) if total_value else 0, 2
                ),
                position_count=len(group),
            )
        )

    total_pnl = total_value - total_cost

    return PortfolioValuationResponse(
        account_id=request.account_id,
        total_cost_basis=round(total_cost, 2),
        total_market_value=round(total_value, 2),
        total_unrealized_pnl=round(total_pnl, 2),
        total_unrealized_pnl_pct=round(
            (total_pnl / total_cost * 100) if total_cost else 0, 2
        ),
        positions=positions if request.include_breakdown else [],
        asset_class_breakdown=breakdowns if request.include_breakdown else [],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
