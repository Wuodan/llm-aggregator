# Repository Guidelines

## Project Structure & Module Organization

Runtime code lives in `src/llm_aggregator`: FastAPI entrypoints in `main.py`/`api.py`, CLI glue in `cli.py`, background
workers under `services/`, and UI artifacts inside `static/`. Model-summary metadata sits in `hf_summary/`. Root-level
`config.yaml` and `config.local.yaml` document deployment knobs, and extra references live in `doc/`. Tests mirror the
package layout under `tests/`, so introduce a sibling test whenever you add a module.

## Build, Test, and Development Commands

<!-- pyml disable line-length -->
- `python -m venv .venv && source .venv/bin/activate` – create a clean interpreter.
- `pip install -r requirements-dev.txt` – pull runtime plus lint/test tooling.
- `ruff check src tests` – enforce python formatting and import hygiene; use `--fix` for auto fixes.
- `pymarkdown --config .pymarkdown.json scan .` – check Markdown formatting. For tables with long lines, wrap them into
  `<!-- pyml disable/enable line-length -->`
- `pytest --cov=src --cov-report=term-missing` – test python code.
- `LLM_AGGREGATOR_CONFIG=./config.local.yaml timeout 120 python -m llm_aggregator >/tmp/llm-aggretator/out.log 2>/tmp/llm-aggretator/err.log` –
boot the FastAPI app locally with the sample config. Start the server wrapped with `timeout` or it will never exit. Pipe
stdout/stderr to files for analysis.
<!-- pyml enable line-length -->

## Coding Style & Naming Conventions

Use four-space indentation, type hints on public functions, and docstrings on API-facing calls. Modules stay snake_case,
classes use CamelCase, and async workers should end with `_job` or `_task` like existing services. Ruff enforces
whitespace, imports, and unused symbols; keep files clean before committing.

## Testing Guidelines

Pytest drives everything. Each feature requires a `test_*.py` sibling covering success and error cases; reuse fixtures
from `tests/conftest.py` and prefer `tmp_path` for scratch files. Check coverage with
`pytest --cov=llm_aggregator --cov-report=term-missing` and keep new code at parity with the file you touched.

## Commit & Pull Request Guidelines

History favors short, imperative subject lines (for example, `Add documentation about OpenAI responses`). Stay under ~60
characters and mention user-visible effects in the body only when necessary. Pull requests must explain the intent, link
issues, enumerate validations (`ruff`, `pytest`, manual UI checks), and attach screenshots or sample JSON whenever UI or
API payloads shift.

## Security & Configuration Tips

Never commit secrets; keep provider credentials in your shell and point `LLM_AGGREGATOR_CONFIG` to a private override
file. When sharing configs, scrub endpoints to placeholders and remove API keys. Sanity-check every provider URL before
committing so teammates do not ping unintended hosts.
