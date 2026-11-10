"""
Mock asset-price data and tool execution.

Provides deterministic price data so the eval suite is fully reproducible
without any network dependency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.tools.schemas import (
    AssetClass,
    AssetPriceResponse,
    GetAssetPriceRequest,
    GetMultipleAssetPricesRequest,
    MultipleAssetPricesResponse,
)

# --------------------------------------------------------------------------- #
#  Static mock price book  (Week 2 will swap in live API calls)
# --------------------------------------------------------------------------- #
MOCK_PRICES: dict[str, dict] = {
    # Equities
    "AAPL":  {"price": 189.84, "asset_class": AssetClass.EQUITY},
    "MSFT":  {"price": 420.55, "asset_class": AssetClass.EQUITY},
    "GOOGL": {"price": 176.32, "asset_class": AssetClass.EQUITY},
    "AMZN":  {"price": 185.60, "asset_class": AssetClass.EQUITY},
    "TSLA":  {"price": 248.42, "asset_class": AssetClass.EQUITY},
    "NVDA":  {"price": 132.65, "asset_class": AssetClass.EQUITY},
    "META":  {"price": 567.12, "asset_class": AssetClass.EQUITY},
    "JPM":   {"price": 198.73, "asset_class": AssetClass.EQUITY},
    # Bonds / Fixed Income
    "TLT":   {"price": 92.45,  "asset_class": AssetClass.BOND},
    "BND":   {"price": 71.38,  "asset_class": AssetClass.BOND},
    "AGG":   {"price": 98.20,  "asset_class": AssetClass.BOND},
    # Gold
    "GLD":   {"price": 221.74, "asset_class": AssetClass.GOLD},
    "XAUUSD": {"price": 2_385.50, "asset_class": AssetClass.GOLD},
    # Crypto
    "BTC-USD": {"price": 68_432.10, "asset_class": AssetClass.CRYPTO},
    "ETH-USD": {"price": 3_521.85, "asset_class": AssetClass.CRYPTO},
    "SOL-USD": {"price": 172.60,   "asset_class": AssetClass.CRYPTO},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
#  Tool implementations
# --------------------------------------------------------------------------- #
def execute_get_asset_price(request: GetAssetPriceRequest) -> AssetPriceResponse:
    """Execute the get_asset_price tool against mock data."""
    symbol = request.symbol.upper()
    if symbol not in MOCK_PRICES:
        raise ValueError(f"Unknown symbol: {symbol}")

    entry = MOCK_PRICES[symbol]
    return AssetPriceResponse(
        symbol=symbol,
        asset_class=entry["asset_class"],
        price=entry["price"],
        currency=request.currency,
        source="mock",
        timestamp=_now_iso(),
    )


def execute_get_multiple_asset_prices(
    request: GetMultipleAssetPricesRequest,
) -> MultipleAssetPricesResponse:
    """Execute the batch price-fetch tool against mock data."""
    results: list[AssetPriceResponse] = []
    errors: list[str] = []

    for asset_req in request.assets:
        try:
            results.append(execute_get_asset_price(asset_req))
        except ValueError:
            errors.append(asset_req.symbol)

    return MultipleAssetPricesResponse(prices=results, errors=errors)


# --------------------------------------------------------------------------- #
#  Dispatcher: route a tool-call name + validated args → result
# --------------------------------------------------------------------------- #
TOOL_REGISTRY = {
    "get_asset_price": (GetAssetPriceRequest, execute_get_asset_price),
    "get_multiple_asset_prices": (
        GetMultipleAssetPricesRequest,
        execute_get_multiple_asset_prices,
    ),
}


def dispatch_tool_call(name: str, arguments: dict) -> str:
    """
    Validate arguments with Pydantic, execute, and return JSON string.
    Raises ValueError on unknown tools or validation failures.
    """
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {name}")

    schema_cls, executor = TOOL_REGISTRY[name]
    request = schema_cls.model_validate(arguments)     # strict validation
    result = executor(request)
    return result.model_dump_json(indent=2)
