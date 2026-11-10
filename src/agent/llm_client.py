"""
LLM client with strict Pydantic JSON enforcement.

Wraps the OpenAI chat-completions API to:
  1. Present tool definitions derived from Pydantic schemas.
  2. Parse and validate tool calls against those schemas.
  3. Execute tools and return results back to the model.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from src.tools.mock_data import dispatch_tool_call
from src.tools.schemas import get_tool_definitions

load_dotenv()

# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #
@dataclass
class LLMConfig:
    model: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    temperature: float = float(os.getenv("TEMPERATURE", "0"))
    max_tokens: int = 4096
    api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set. Copy .env.example → .env and fill it in.")


# --------------------------------------------------------------------------- #
#  Agent runner
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = """\
You are a portfolio management assistant. When the user asks about asset prices,
you MUST call the appropriate tool rather than guessing. Always use the tools
provided. Do NOT fabricate prices.

Available asset symbols include:
Equities: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, JPM
Bonds:    TLT, BND, AGG
Gold:     GLD, XAUUSD
Crypto:   BTC-USD, ETH-USD, SOL-USD
"""


@dataclass
class ToolCallResult:
    """Record of a single tool call and its outcome."""

    tool_name: str
    arguments: dict
    result_json: str
    success: bool
    error: Optional[str] = None


@dataclass
class AgentResponse:
    """Full response from one agent turn (may involve multiple tool calls)."""

    final_text: str
    tool_calls: list[ToolCallResult] = field(default_factory=list)
    raw_messages: list[dict] = field(default_factory=list)


def run_agent(
    user_prompt: str,
    config: LLMConfig | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> AgentResponse:
    """
    Send *user_prompt* to the LLM, execute any tool calls it makes, and
    return the final assistant text plus a log of every tool invocation.
    """
    cfg = config or LLMConfig()
    client = OpenAI(api_key=cfg.api_key)
    tools = get_tool_definitions()

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    tool_call_log: list[ToolCallResult] = []

    # Loop: the model may make multiple rounds of tool calls
    for _ in range(10):  # safety cap
        response = client.chat.completions.create(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        # If the model has no tool calls, we're done
        if not msg.tool_calls:
            return AgentResponse(
                final_text=msg.content or "",
                tool_calls=tool_call_log,
                raw_messages=messages + [{"role": "assistant", "content": msg.content}],
            )

        # Process each tool call
        assistant_msg = {
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        }
        messages.append(assistant_msg)

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            try:
                result_json = dispatch_tool_call(tc.function.name, args)
                success = True
                error = None
            except Exception as e:
                result_json = json.dumps({"error": str(e)})
                success = False
                error = str(e)

            tool_call_log.append(
                ToolCallResult(
                    tool_name=tc.function.name,
                    arguments=args,
                    result_json=result_json,
                    success=success,
                    error=error,
                )
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_json,
                }
            )

    # Fell through the safety cap
    return AgentResponse(
        final_text="[Agent exceeded maximum tool-call rounds]",
        tool_calls=tool_call_log,
        raw_messages=messages,
    )
