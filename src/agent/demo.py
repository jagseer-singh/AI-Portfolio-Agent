"""
Quick demo: call the agent with a sample prompt and print results.

Usage:
    python -m src.agent.demo
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agent.llm_client import LLMConfig, run_agent


def main():
    prompts = [
        "What is the current price of Apple stock?",
        "Show me the prices of BTC-USD, ETH-USD, and GLD.",
        "Which is more expensive, NVIDIA or Meta stock?",
    ]

    try:
        config = LLMConfig()
    except ValueError as e:
        print(f"⚠️  {e}")
        print("Copy .env.example → .env and add your OpenAI API key.")
        return

    for prompt in prompts:
        print(f"\n{'═'*60}")
        print(f"User: {prompt}")
        print(f"{'─'*60}")

        response = run_agent(prompt, config=config)

        if response.tool_calls:
            for tc in response.tool_calls:
                status = "✓" if tc.success else "✗"
                print(f"  [{status}] Tool: {tc.tool_name}({tc.arguments})")

        print(f"\nAssistant: {response.final_text}")


if __name__ == "__main__":
    main()
