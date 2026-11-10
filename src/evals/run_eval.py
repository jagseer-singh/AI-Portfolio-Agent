"""
Eval runner — executes the full eval suite and logs results.

Usage:
    python -m src.evals.run_eval          # run all cases
    python -m src.evals.run_eval --dry    # show cases without calling the LLM
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from src.agent.llm_client import AgentResponse, LLMConfig, run_agent
from evals.prompts.eval_cases import EVAL_CASES, EvalCase

RESULTS_DIR = PROJECT_ROOT / "evals" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
#  Scoring
# --------------------------------------------------------------------------- #
@dataclass
class EvalScore:
    case_id: str
    category: str
    prompt: str
    tool_called_correctly: bool
    symbols_correct: bool
    answer_contains_expected: bool
    overall_pass: bool
    tools_used: str  # comma-separated list of tools the agent actually called
    symbols_used: str  # comma-separated list of symbols seen
    final_answer_snippet: str  # first 200 chars
    error: str = ""


def _score_case(case: EvalCase, response: AgentResponse) -> EvalScore:
    """Score a single eval case against the agent response."""
    # 1. Tool selection check
    tools_used = [tc.tool_name for tc in response.tool_calls]
    if case.expected_tool is None:
        tool_correct = len(tools_used) == 0
    else:
        tool_correct = case.expected_tool in tools_used

    # 2. Symbol check — all expected symbols should appear in tool-call args
    all_args_json = json.dumps([tc.arguments for tc in response.tool_calls]).upper()
    symbols_correct = all(sym.upper() in all_args_json for sym in case.expected_symbols)

    # 3. Answer content check
    answer_lower = response.final_text.lower()
    if case.expected_in_answer:
        answer_ok = any(exp.lower() in answer_lower for exp in case.expected_in_answer)
    else:
        answer_ok = True  # no content assertion

    overall = tool_correct and symbols_correct and answer_ok

    return EvalScore(
        case_id=case.id,
        category=case.category,
        prompt=case.prompt,
        tool_called_correctly=tool_correct,
        symbols_correct=symbols_correct,
        answer_contains_expected=answer_ok,
        overall_pass=overall,
        tools_used=",".join(tools_used),
        symbols_used=",".join(
            s.upper()
            for tc in response.tool_calls
            for s in _extract_symbols(tc.arguments)
        ),
        final_answer_snippet=response.final_text[:200],
    )


def _extract_symbols(args: dict) -> list[str]:
    """Pull symbol strings out of tool-call arguments."""
    symbols = []
    if "symbol" in args:
        symbols.append(args["symbol"])
    if "assets" in args:
        for a in args["assets"]:
            if "symbol" in a:
                symbols.append(a["symbol"])
    return symbols


# --------------------------------------------------------------------------- #
#  Git metadata
# --------------------------------------------------------------------------- #
def _get_git_commit() -> str:
    """Return current short git SHA, or 'no-git' if unavailable."""
    try:
        # Try portable git first, then system git
        git_paths = [
            r"C:\Users\acer\PortableGit\bin\git.exe",
            "git",
        ]
        for git_cmd in git_paths:
            try:
                result = subprocess.run(
                    [git_cmd, "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=str(PROJECT_ROOT),
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except FileNotFoundError:
                continue
    except Exception:
        pass
    return "no-git"


# --------------------------------------------------------------------------- #
#  CSV logging
# --------------------------------------------------------------------------- #
CSV_FIELDS = [
    "timestamp",
    "git_commit",
    "model_name",
    "temperature",
    "case_id",
    "category",
    "prompt",
    "tool_called_correctly",
    "symbols_correct",
    "answer_contains_expected",
    "overall_pass",
    "tools_used",
    "symbols_used",
    "final_answer_snippet",
    "error",
]


def _append_to_csv(
    scores: list[EvalScore],
    config: LLMConfig,
    git_commit: str,
    csv_path: Path,
):
    """Append eval scores to the cumulative CSV log."""
    ts = datetime.now(timezone.utc).isoformat()
    file_exists = csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        for s in scores:
            row = {
                "timestamp": ts,
                "git_commit": git_commit,
                "model_name": config.model,
                "temperature": config.temperature,
                **{k: v for k, v in asdict(s).items() if k in CSV_FIELDS},
            }
            writer.writerow(row)


# --------------------------------------------------------------------------- #
#  Pretty printing
# --------------------------------------------------------------------------- #
def _print_summary(scores: list[EvalScore], config: LLMConfig, git_commit: str):
    """Print a rich summary table to the terminal."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()

        console.print(f"\n[bold cyan]═══ Eval Run Summary ═══[/bold cyan]")
        console.print(f"  Model:       {config.model}")
        console.print(f"  Temperature: {config.temperature}")
        console.print(f"  Git commit:  {git_commit}")
        console.print(f"  Cases:       {len(scores)}")
        console.print()

        table = Table(show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Category")
        table.add_column("Tool ✓", justify="center")
        table.add_column("Symbols ✓", justify="center")
        table.add_column("Answer ✓", justify="center")
        table.add_column("Pass", justify="center")
        table.add_column("Error")

        for s in scores:
            pass_style = "green" if s.overall_pass else "red"
            table.add_row(
                s.case_id,
                s.category,
                "✓" if s.tool_called_correctly else "✗",
                "✓" if s.symbols_correct else "✗",
                "✓" if s.answer_contains_expected else "✗",
                f"[{pass_style}]{'PASS' if s.overall_pass else 'FAIL'}[/{pass_style}]",
                s.error or "",
            )

        console.print(table)

        passed = sum(1 for s in scores if s.overall_pass)
        total = len(scores)
        pct = (passed / total * 100) if total else 0
        style = "green" if pct >= 80 else "yellow" if pct >= 60 else "red"
        console.print(f"\n  [bold {style}]Score: {passed}/{total} ({pct:.1f}%)[/bold {style}]\n")

        # Category breakdown
        categories: dict[str, list[bool]] = {}
        for s in scores:
            categories.setdefault(s.category, []).append(s.overall_pass)
        console.print("  [bold]By category:[/bold]")
        for cat, results in sorted(categories.items()):
            p = sum(results)
            t = len(results)
            console.print(f"    {cat:12s}: {p}/{t}")
        console.print()

    except ImportError:
        # Fallback if rich is not installed
        passed = sum(1 for s in scores if s.overall_pass)
        total = len(scores)
        print(f"\nEval: {passed}/{total} passed ({passed/total*100:.1f}%)")
        for s in scores:
            status = "PASS" if s.overall_pass else "FAIL"
            print(f"  [{status}] {s.case_id}: tool={s.tool_called_correctly} sym={s.symbols_correct} ans={s.answer_contains_expected}")


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #
def run_eval(
    cases: list[EvalCase] | None = None,
    config: LLMConfig | None = None,
    runs_per_case: int = 1,
    delay: float = 4.0,
) -> list[EvalScore]:
    """Run the full eval suite and return scores."""
    cases = cases or EVAL_CASES
    cfg = config or LLMConfig()
    git_commit = _get_git_commit()
    csv_path = RESULTS_DIR / "eval_log.csv"

    all_scores: list[EvalScore] = []

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] Evaluating: {case.id} ({case.category})", flush=True)
        best_score = None
        for run_idx in range(runs_per_case):
            try:
                response = run_agent(case.prompt, config=cfg)
                score = _score_case(case, response)
            except Exception as e:
                score = EvalScore(
                    case_id=case.id,
                    category=case.category,
                    prompt=case.prompt,
                    tool_called_correctly=False,
                    symbols_correct=False,
                    answer_contains_expected=False,
                    overall_pass=False,
                    tools_used="",
                    symbols_used="",
                    final_answer_snippet="",
                    error=str(e),
                )

            # For multi-run: keep the best result (most optimistic)
            if best_score is None or (score.overall_pass and not best_score.overall_pass):
                best_score = score

        all_scores.append(best_score)  # type: ignore[arg-type]
        if delay > 0 and i < len(cases):
            time.sleep(delay)

    _append_to_csv(all_scores, cfg, git_commit, csv_path)
    _print_summary(all_scores, cfg, git_commit)

    return all_scores


def main():
    parser = argparse.ArgumentParser(description="Run portfolio agent eval suite")
    parser.add_argument("--dry", action="store_true", help="List cases without running")
    parser.add_argument("--runs", type=int, default=1, help="Runs per case (for non-zero temp)")
    parser.add_argument("--model", type=str, default=None, help="Override model name")
    parser.add_argument("--temperature", type=float, default=None, help="Override temperature")
    parser.add_argument("--delay", type=float, default=4.0, help="Delay between cases in seconds")
    args = parser.parse_args()

    if args.dry:
        for c in EVAL_CASES:
            print(f"  [{c.category:8s}] {c.id:20s} → {c.prompt[:60]}")
        print(f"\n  Total: {len(EVAL_CASES)} cases")
        return

    cfg = LLMConfig()
    if args.model:
        cfg.model = args.model
    if args.temperature is not None:
        cfg.temperature = args.temperature

    # If temperature > 0 and no explicit --runs, default to 3
    runs = args.runs
    if cfg.temperature > 0 and runs == 1:
        print("Note: temperature > 0 detected, running each case 3 times (override with --runs)")
        runs = 3

    scores = run_eval(config=cfg, runs_per_case=runs, delay=args.delay)

    # Exit with error code if pass rate < 80%
    passed = sum(1 for s in scores if s.overall_pass)
    if passed / len(scores) < 0.8:
        sys.exit(1)


if __name__ == "__main__":
    main()
