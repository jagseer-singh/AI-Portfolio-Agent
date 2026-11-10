"""
Pydantic schemas for deterministic tool calling.

These schemas enforce strict JSON output from the LLM, ensuring
every tool call is fully validated before execution.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
#  Asset class enum — the universe of assets the agent knows about
# --------------------------------------------------------------------------- #
class AssetClass(str, Enum):
    EQUITY = "equity"
    BOND = "bond"
    GOLD = "gold"
    CRYPTO = "crypto"
    CASH = "cash"


# --------------------------------------------------------------------------- #
#  Tool-call request schemas (what the LLM must produce)
# --------------------------------------------------------------------------- #
class GetAssetPriceRequest(BaseModel):
    """Request schema the LLM must fill to invoke the get_asset_price tool."""

    symbol: str = Field(
        ...,
        description="Ticker or identifier, e.g. 'AAPL', 'BTC-USD', 'GLD'.",
        min_length=1,
        max_length=20,
    )
    asset_class: AssetClass = Field(
        ...,
        description="The asset class this symbol belongs to.",
    )
    currency: str = Field(
        default="USD",
        description="Currency to quote the price in (ISO 4217).",
        min_length=3,
        max_length=3,
    )


class GetMultipleAssetPricesRequest(BaseModel):
    """Batch variant — fetch several prices in one call."""

    assets: list[GetAssetPriceRequest] = Field(
        ...,
        description="List of assets to look up.",
        min_length=1,
        max_length=50,
    )


# --------------------------------------------------------------------------- #
#  Tool-call response schemas (what the tool returns)
# --------------------------------------------------------------------------- #
class AssetPriceResponse(BaseModel):
    """Single-asset price result."""

    symbol: str
    asset_class: AssetClass
    price: float = Field(..., description="Current price in the requested currency.")
    currency: str = Field(default="USD")
    source: str = Field(default="mock", description="Data source identifier.")
    timestamp: str = Field(..., description="ISO-8601 timestamp of the quote.")


class MultipleAssetPricesResponse(BaseModel):
    """Batch price result."""

    prices: list[AssetPriceResponse]
    errors: list[str] = Field(default_factory=list, description="Symbols that failed lookup.")


# --------------------------------------------------------------------------- #
#  Tool definition helpers — convert schemas → OpenAI function-tool format
# --------------------------------------------------------------------------- #
def get_tool_definitions() -> list[dict]:
    """Return OpenAI-compatible tool definitions derived from our Pydantic schemas."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_asset_price",
                "description": (
                    "Fetch the current price for a single asset. "
                    "Returns the price, asset class, currency, and data source."
                ),
                "parameters": GetAssetPriceRequest.model_json_schema(),
                "strict": True,     # ← forces structured output
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_multiple_asset_prices",
                "description": (
                    "Fetch current prices for multiple assets in a single batch call."
                ),
                "parameters": GetMultipleAssetPricesRequest.model_json_schema(),
                "strict": True,
            },
        },
    ]
