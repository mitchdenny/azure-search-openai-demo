# Instructions for coding agents

This fork is an Aspire template adapted from Azure-Samples/azure-search-openai-demo.
Keep these instructions current when changing code or development processes.

## Layout

* `apphost.mts`: TypeScript AppHost for Azure Storage, Search, OpenAI deployments,
  backend/frontend and explicitly started `ingest`, dynamic endpoints and health checks.
* `aspire.config.json`: SDK/integration versions and dashboard profiles.
* `.template.config`: unpacked .NET engine template and Aspire CLI host metadata.
* `app/backend`: Python Quart API. `approaches` implements RAG; Jinja2 prompts are
  under `approaches/prompts`; `core/authentication.py` implements Entra/OBO.
* `app/backend/prepdocslib`: ingestion library shared with cloud Functions.
* `app/functions`: optional cloud ingestion Functions. Run
  `python scripts/copy_prepdocslib.py` after changing the library; generated copies
  and function requirements are not tracked.
* `app/frontend`: React/TypeScript Vite app; API client in `src/api`, UI in
  `src/components` and `src/pages`, all translations in `src/locales`.
* `scripts`: explicit ingestion, ACL, Graph registration and maintenance utilities.
* `tests`: pytest unit/integration tests and Playwright `e2e.py`.
* `evals`: evaluation tools, raw `results`, derived `results_summaries`, and
  `results_comparisons`. Do not include raw runs in generated templates.

## Local development and configuration

Follow `docs/localdev.md`. Run `aspire restore` then
`aspire start --non-interactive --isolated --apphost apphost.mts` for agent work in
a worktree; wait for backend/frontend with `aspire wait`. Stop only the exact
AppHost you started. Never disturb other apps/worktrees.
AppHost uses npm (`package-lock.json`); frontend has its own npm lockfile.
Create root `.venv` with Python 3.13 before startup; Aspire does not create it
using the system default Python. `.python-version` selects 3.13 for uv/pyenv.
Never edit generated `.aspire/modules`. Use `aspire add` / `aspire restore`.
Verify unfamiliar Aspire APIs with docs and generated read-only signatures.

The template is opinionated: declare Azure resources and model deployments in the
AppHost and wire their outputs to consumers. Do not restore `.env` loading, provider
selection, environment forwarding loops or a second configuration validator there.
Standalone ingestion/admin utilities may use `.env`; the application entry point
does not load it. Mark any explicitly added credential parameter secret.
The `ingest` resource receives AppHost outputs and uses `--no-env-file`. It shares
the backend's Python environment and waits for the backend before manual Start.
Do not make ingestion automatic: it mutates Azure data and calls a paid model.
There is no AZD state or provisioning workflow.

AppHost startup can provision real Azure services and role assignments. Do not start
it without authorization for those effects. Do not provision resources,
mutate IAM, run ingestion or paid model calls without authorization. Startup health
means process readiness, not verified Azure credentials/index/model access.
Use `az login` for local credentials. Preserve managed identity in deployed hosts.

## Template invariants

Stable SDK/integration defaults are 13.6.4. Keep `AspireVersion` string replacement
scoped to the SDK field; resolve hosting integration versions
independently using host `nugetPackageVersion` sources. Do not hardcode PR feeds,
machine paths, secrets or generated modules. Custom Git/directory generation needs
the feature CLI from microsoft/aspire#21263; generation executes no restore/scripts.
Test a fresh renamed output and a pushed full-commit source, not just source files.
Preserve MIT license and upstream attribution.

## Tests and style

Activate `.venv` before Python checks:

```sh
source .venv/bin/activate
pytest tests/
ruff check .
black . --check
ty check
```

Build frontend with `npm --prefix app/frontend run build` before app/E2E tests
which serve static assets. Run `pytest tests/e2e.py` after Playwright Chromium is
installed. Mocks come from `tests/conftest.py`; prefer HTTP-level mocks.
Add unit tests for helpers, app tests for routes, E2E tests for UI features.
Use the smallest relevant test selection first. Coverage:
`pytest --cov --cov-report=annotate:cov_annotate`.

Use `npm run build` to lint/type-check the AppHost after `aspire restore`.
Python code uses ruff/black; do not prefix private application helpers with `_`.
Type-check application/scripts with `ty check`; tests are excluded.
Never hide failures or substitute fake success for real-service behavior.

Compile backend dependencies from `app/backend`:
`uv pip compile requirements.in -o requirements.txt --python-version 3.10`.
Use `--upgrade-package <package>` only for an intentional upgrade.
Frontend changes use its npm lockfile and `npm run build`. MSAL upgrades require
manual popup, redirect bridge, OBO and ACL checks described in `docs/login_and_acl.md`.
Graph SDK upgrades additionally require authorized create/update registration tests;
unit mocks alone are insufficient.

New developer settings need API override types, Settings UI, Chat state/wiring,
translations in every locale, backend overrides and possibly `/config`.
Use the repository pull-request template when creating PRs.
