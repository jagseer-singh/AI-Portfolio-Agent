"""
Market data provider — pluggable price source.

Provides a unified interface for fetching prices from:
  1. Mock data (default, deterministic)
  2. Live APIs (opt-in, for demo purposes)

Week 2 introduces the provider pattern so live APIs can be
swapped in without changing tool schemas or the agent.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum

from src.tools.schemas import (
    AssetClass,
    AssetPriceResponse,
    GetAssetPriceRequest,
)


class PriceSource(str, Enum):
    MOCK = "mock"
    YAHOO = "yahoo"       # future: yfinance
    COINGECKO = "coingecko"  # future: free crypto API


class PriceProvider(ABC):
    """Abstract price provider interface."""

    @abstractmethod
    def get_price(self, request: GetAssetPriceRequest) -> AssetPriceResponse:
        """Fetch a single asset price."""
        ...

    @abstractmethod
    def source_name(self) -> str:
        """Return the data source identifier."""
        ...


class MockPriceProvider(PriceProvider):
    """Provides deterministic mock prices (default)."""

    def __init__(self):
        from src.tools.mock_data import MOCK_PRICES
        self._prices = MOCK_PRICES

    def get_price(self, request: GetAssetPriceRequest) -> AssetPriceResponse:
        symbol = request.symbol.upper()
        if symbol not in self._prices:
            raise ValueError(f"Unknown symbol: {symbol}")

        entry = self._prices[symbol]
        return AssetPriceResponse(
            symbol=symbol,
            asset_class=entry["asset_class"],
            price=entry["price"],
            currency=request.currency,
            source=self.source_name(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def source_name(self) -> str:
        return "mock"


# --------------------------------------------------------------------------- #
#  Provider registry
# --------------------------------------------------------------------------- #
_current_provider: PriceProvider | None = None


def get_price_provider() -> PriceProvider:
    """Get the active price provider (lazy-init to mock by default)."""
    global _current_provider
    if _current_provider is None:
        source = os.getenv("PRICE_SOURCE", "mock").lower()
        if source == "mock":
            _current_provider = MockPriceProvider()
        else:
            # Extensibility point for Week 2+ live APIs
            _current_provider = MockPriceProvider()
    return _current_provider


def set_price_provider(provider: PriceProvider) -> None:
    """Override the active price provider (useful for testing)."""
    global _current_provider
    _current_provider = provider


def reset_price_provider() -> None:
    """Reset to default (re-reads env on next call)."""
    global _current_provider
    _current_provider = None
