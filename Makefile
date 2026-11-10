# Portfolio Management Agent — Makefile
# =====================================
# Usage:
#   make test     — run unit tests
#   make eval     — run eval suite (temperature 0, logs git commit + model)
#   make eval-3x  — run eval 3× per case (for non-zero temperature)
#   make demo     — run interactive demo
#   make lint     — run ruff linter

PYTHON = .venv/Scripts/python.exe
PIP    = .venv/Scripts/pip.exe

.PHONY: test eval eval-3x demo lint setup clean

# ─── Setup ──────────────────────────────────────────────────────────────────
setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install pydantic openai python-dotenv rich pytest ruff mypy

# ─── Tests ──────────────────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/ -v

# ─── Evals ──────────────────────────────────────────────────────────────────
eval:
	$(PYTHON) -m src.evals.run_eval --temperature 0

eval-3x:
	$(PYTHON) -m src.evals.run_eval --temperature 0.2 --runs 3

eval-dry:
	$(PYTHON) -m src.evals.run_eval --dry

# ─── Demo ───────────────────────────────────────────────────────────────────
demo:
	$(PYTHON) -m src.agent.demo

# ─── Lint ───────────────────────────────────────────────────────────────────
lint:
	.venv/Scripts/ruff.exe check src/ tests/ evals/

# ─── Clean ──────────────────────────────────────────────────────────────────
clean:
	del /s /q __pycache__ 2>nul
	del /s /q *.pyc 2>nul
