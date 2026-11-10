"""
Unit tests for Pydantic schemas and mock tool execution.
Tests that schemas validate correctly and tools return expected mock data.
"""

from __future__ import annotations

import json
import pytest

from src.tools.schemas import (
    AssetClass,
    GetAssetPriceRequest,
    GetMultipleAssetPricesRequest,
    AssetPriceResponse,
    get_tool_definitions,
)
from src.tools.mock_data import (
    dispatch_tool_call,
    execute_get_asset_price,
    execute_get_multiple_asset_prices,
    MOCK_PRICES,
)


# --------------------------------------------------------------------------- #
#  Schema validation tests
# --------------------------------------------------------------------------- #
class TestSchemaValidation:
    def test_valid_single_request(self):
        req = GetAssetPriceRequest(symbol="AAPL", asset_class=AssetClass.EQUITY)
        assert req.symbol == "AAPL"
        assert req.currency == "USD"

    def test_valid_batch_request(self):
        req = GetMultipleAssetPricesRequest(
            assets=[
                GetAssetPriceRequest(symbol="AAPL", asset_class=AssetClass.EQUITY),
                GetAssetPriceRequest(symbol="BTC-USD", asset_class=AssetClass.CRYPTO),
            ]
        )
        assert len(req.assets) == 2

    def test_invalid_empty_symbol(self):
        with pytest.raises(Exception):
            GetAssetPriceRequest(symbol="", asset_class=AssetClass.EQUITY)

    def test_invalid_long_symbol(self):
        with pytest.raises(Exception):
            GetAssetPriceRequest(symbol="A" * 21, asset_class=AssetClass.EQUITY)

    def test_invalid_asset_class(self):
        with pytest.raises(Exception):
            GetAssetPriceRequest(symbol="AAPL", asset_class="invalid")  # type: ignore

    def test_invalid_currency_length(self):
        with pytest.raises(Exception):
            GetAssetPriceRequest(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="US")


# --------------------------------------------------------------------------- #
#  Mock data execution tests
# --------------------------------------------------------------------------- #
class TestMockExecution:
    def test_single_price_lookup(self):
        req = GetAssetPriceRequest(symbol="AAPL", asset_class=AssetClass.EQUITY)
        resp = execute_get_asset_price(req)
        assert resp.symbol == "AAPL"
        assert resp.price == 189.84
        assert resp.source == "mock"

    def test_case_insensitive_lookup(self):
        req = GetAssetPriceRequest(symbol="aapl", asset_class=AssetClass.EQUITY)
        resp = execute_get_asset_price(req)
        assert resp.symbol == "AAPL"

    def test_unknown_symbol_raises(self):
        req = GetAssetPriceRequest(symbol="XYZFAKE", asset_class=AssetClass.EQUITY)
        with pytest.raises(ValueError, match="Unknown symbol"):
            execute_get_asset_price(req)

    def test_batch_price_lookup(self):
        req = GetMultipleAssetPricesRequest(
            assets=[
                GetAssetPriceRequest(symbol="AAPL", asset_class=AssetClass.EQUITY),
                GetAssetPriceRequest(symbol="BTC-USD", asset_class=AssetClass.CRYPTO),
                GetAssetPriceRequest(symbol="GLD", asset_class=AssetClass.GOLD),
            ]
        )
        resp = execute_get_multiple_asset_prices(req)
        assert len(resp.prices) == 3
        assert len(resp.errors) == 0

    def test_batch_with_unknown(self):
        req = GetMultipleAssetPricesRequest(
            assets=[
                GetAssetPriceRequest(symbol="AAPL", asset_class=AssetClass.EQUITY),
                GetAssetPriceRequest(symbol="FAKE", asset_class=AssetClass.EQUITY),
            ]
        )
        resp = execute_get_multiple_asset_prices(req)
        assert len(resp.prices) == 1
        assert "FAKE" in resp.errors

    def test_all_mock_symbols_are_valid(self):
        """Every symbol in MOCK_PRICES should be fetchable."""
        for sym, data in MOCK_PRICES.items():
            req = GetAssetPriceRequest(symbol=sym, asset_class=data["asset_class"])
            resp = execute_get_asset_price(req)
            assert resp.price == data["price"]


# --------------------------------------------------------------------------- #
#  Dispatch tests
# --------------------------------------------------------------------------- #
class TestDispatch:
    def test_dispatch_single(self):
        result_json = dispatch_tool_call(
            "get_asset_price",
            {"symbol": "MSFT", "asset_class": "equity"},
        )
        result = json.loads(result_json)
        assert result["price"] == 420.55

    def test_dispatch_batch(self):
        result_json = dispatch_tool_call(
            "get_multiple_asset_prices",
            {
                "assets": [
                    {"symbol": "AAPL", "asset_class": "equity"},
                    {"symbol": "ETH-USD", "asset_class": "crypto"},
                ]
            },
        )
        result = json.loads(result_json)
        assert len(result["prices"]) == 2

    def test_dispatch_unknown_tool(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            dispatch_tool_call("nonexistent_tool", {})

    def test_dispatch_invalid_args(self):
        with pytest.raises(Exception):
            dispatch_tool_call("get_asset_price", {"symbol": "", "asset_class": "equity"})


# --------------------------------------------------------------------------- #
#  Tool definition tests
# --------------------------------------------------------------------------- #
class TestToolDefinitions:
    def test_definitions_structure(self):
        tools = get_tool_definitions()
        assert len(tools) == 2
        for tool in tools:
            assert tool["type"] == "function"
            assert "name" in tool["function"]
            assert "parameters" in tool["function"]
            assert tool["function"]["strict"] is True

    def test_definitions_have_required_fields(self):
        tools = get_tool_definitions()
        names = {t["function"]["name"] for t in tools}
        assert "get_asset_price" in names
        assert "get_multiple_asset_prices" in names
