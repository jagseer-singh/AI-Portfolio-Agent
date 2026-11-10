"""
Eval prompt bank — 25 varied prompts with expected ground-truth answers.

Each case specifies:
  - id: unique identifier
  - prompt: what to send the agent
  - expected_tool: the tool the agent should call (or None for no-tool)
  - expected_symbols: symbols that should appear in tool calls
  - expected_in_answer: substrings that must appear in the final answer
  - category: for grouping metrics
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    id: str
    prompt: str
    expected_tool: str | None
    expected_symbols: list[str] = field(default_factory=list)
    expected_in_answer: list[str] = field(default_factory=list)
    category: str = "general"


EVAL_CASES: list[EvalCase] = [
    # ---- Single equity lookups ----
    EvalCase(
        id="eq_aapl",
        prompt="What is the current price of Apple stock?",
        expected_tool="get_asset_price",
        expected_symbols=["AAPL"],
        expected_in_answer=["189.84"],
        category="equity",
    ),
    EvalCase(
        id="eq_msft",
        prompt="How much is Microsoft trading at right now?",
        expected_tool="get_asset_price",
        expected_symbols=["MSFT"],
        expected_in_answer=["420.55"],
        category="equity",
    ),
    EvalCase(
        id="eq_googl",
        prompt="Get me the Google stock price.",
        expected_tool="get_asset_price",
        expected_symbols=["GOOGL"],
        expected_in_answer=["176.32"],
        category="equity",
    ),
    EvalCase(
        id="eq_tsla",
        prompt="What's Tesla's share price?",
        expected_tool="get_asset_price",
        expected_symbols=["TSLA"],
        expected_in_answer=["248.42"],
        category="equity",
    ),
    EvalCase(
        id="eq_nvda",
        prompt="NVIDIA stock price please.",
        expected_tool="get_asset_price",
        expected_symbols=["NVDA"],
        expected_in_answer=["132.65"],
        category="equity",
    ),
    EvalCase(
        id="eq_meta",
        prompt="How much is Meta Platforms trading at?",
        expected_tool="get_asset_price",
        expected_symbols=["META"],
        expected_in_answer=["567.12"],
        category="equity",
    ),
    EvalCase(
        id="eq_jpm",
        prompt="What's the current JPMorgan stock price?",
        expected_tool="get_asset_price",
        expected_symbols=["JPM"],
        expected_in_answer=["198.73"],
        category="equity",
    ),
    EvalCase(
        id="eq_amzn",
        prompt="Show me Amazon's price.",
        expected_tool="get_asset_price",
        expected_symbols=["AMZN"],
        expected_in_answer=["185.60"],
        category="equity",
    ),
    # ---- Bond lookups ----
    EvalCase(
        id="bond_tlt",
        prompt="What is the price of TLT (20-year Treasury bond ETF)?",
        expected_tool="get_asset_price",
        expected_symbols=["TLT"],
        expected_in_answer=["92.45"],
        category="bond",
    ),
    EvalCase(
        id="bond_bnd",
        prompt="Give me the BND bond ETF price.",
        expected_tool="get_asset_price",
        expected_symbols=["BND"],
        expected_in_answer=["71.38"],
        category="bond",
    ),
    EvalCase(
        id="bond_agg",
        prompt="How much is AGG trading at?",
        expected_tool="get_asset_price",
        expected_symbols=["AGG"],
        expected_in_answer=["98.20"],
        category="bond",
    ),
    # ---- Gold lookups ----
    EvalCase(
        id="gold_gld",
        prompt="What is the GLD ETF price?",
        expected_tool="get_asset_price",
        expected_symbols=["GLD"],
        expected_in_answer=["221.74"],
        category="gold",
    ),
    EvalCase(
        id="gold_spot",
        prompt="What's the current spot gold price in USD?",
        expected_tool="get_asset_price",
        expected_symbols=["XAUUSD"],
        expected_in_answer=["2385", "2,385"],
        category="gold",
    ),
    # ---- Crypto lookups ----
    EvalCase(
        id="crypto_btc",
        prompt="Bitcoin price?",
        expected_tool="get_asset_price",
        expected_symbols=["BTC-USD"],
        expected_in_answer=["68432", "68,432"],
        category="crypto",
    ),
    EvalCase(
        id="crypto_eth",
        prompt="How much is Ethereum right now?",
        expected_tool="get_asset_price",
        expected_symbols=["ETH-USD"],
        expected_in_answer=["3521", "3,521"],
        category="crypto",
    ),
    EvalCase(
        id="crypto_sol",
        prompt="Get Solana's current price.",
        expected_tool="get_asset_price",
        expected_symbols=["SOL-USD"],
        expected_in_answer=["172.60"],
        category="crypto",
    ),
    # ---- Batch / multi-asset lookups ----
    EvalCase(
        id="multi_tech",
        prompt="What are the prices of AAPL, MSFT, and GOOGL?",
        expected_tool="get_multiple_asset_prices",
        expected_symbols=["AAPL", "MSFT", "GOOGL"],
        expected_in_answer=["189.84", "420.55", "176.32"],
        category="multi",
    ),
    EvalCase(
        id="multi_mixed",
        prompt="Give me prices for AAPL, BTC-USD, and GLD.",
        expected_tool="get_multiple_asset_prices",
        expected_symbols=["AAPL", "BTC-USD", "GLD"],
        expected_in_answer=["189.84"],
        category="multi",
    ),
    EvalCase(
        id="multi_crypto",
        prompt="Show me all crypto prices: BTC, ETH, SOL.",
        expected_tool="get_multiple_asset_prices",
        expected_symbols=["BTC-USD", "ETH-USD", "SOL-USD"],
        expected_in_answer=["68432", "68,432"],
        category="multi",
    ),
    # ---- Comparative / analytical prompts ----
    EvalCase(
        id="compare_eq",
        prompt="Which is more expensive right now, Apple or Microsoft stock?",
        expected_tool="get_multiple_asset_prices",
        expected_symbols=["AAPL", "MSFT"],
        expected_in_answer=["MSFT", "Microsoft"],
        category="analysis",
    ),
    EvalCase(
        id="compare_crypto",
        prompt="Is Bitcoin or Ethereum more expensive? By how much?",
        expected_tool="get_multiple_asset_prices",
        expected_symbols=["BTC-USD", "ETH-USD"],
        expected_in_answer=["Bitcoin", "BTC"],
        category="analysis",
    ),
    # ---- Edge / tricky prompts ----
    EvalCase(
        id="edge_unknown",
        prompt="What's the price of XYZFAKE stock?",
        expected_tool="get_asset_price",
        expected_symbols=["XYZFAKE"],
        expected_in_answer=[],
        category="edge",
    ),
    EvalCase(
        id="edge_no_tool",
        prompt="What is a stock?",
        expected_tool=None,
        expected_symbols=[],
        expected_in_answer=["stock"],
        category="edge",
    ),
    EvalCase(
        id="edge_ambiguous",
        prompt="How much is gold?",
        expected_tool="get_asset_price",
        expected_symbols=["GLD", "XAUUSD"],
        expected_in_answer=[],
        category="edge",
    ),
    EvalCase(
        id="edge_natural",
        prompt="I want to know if I should buy Tesla. What's the price?",
        expected_tool="get_asset_price",
        expected_symbols=["TSLA"],
        expected_in_answer=["248.42"],
        category="edge",
    ),
]
