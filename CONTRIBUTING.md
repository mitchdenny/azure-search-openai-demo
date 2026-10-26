# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

- [Submitting a Pull Request (PR)](#submitting-a-pull-request-pr)
- [Setting up the development environment](#setting-up-the-development-environment)
- [Running unit tests](#running-unit-tests)
- [Running E2E tests](#running-e2e-tests)
- [Code style](#code-style)
- [Adding new features](#adding-new-features)
  - [Adding environment variables](#adding-environment-variables)
  - [Adding new UI strings](#adding-new-ui-strings)

## Submitting a Pull Request (PR)

Before you submit your Pull Request (PR) consider the following guidelines:

- Search the repository (<https://github.com/[organization-name>]/[repository-name]/pulls) for an open or closed PR
  that relates to your submission. You don't want to duplicate effort.
- Make your changes in a new git fork
- Follow [Code style conventions](#code-style)
- [Run the tests](#running-unit-tests) (and write new ones, if needed)
- Commit your changes using a descriptive commit message
- Push your fork to GitHub
- In GitHub, create a pull request to the `main` branch of the repository
- Ask a maintainer to review your PR and address any comments they might have

## Setting up the development environment

Install the development dependencies:

```shell
uv sync --locked --default-index https://pypi.org/simple
source .venv/bin/activate
uv pip install -r requirements-dev.txt
```

For application startup and Azure prerequisites, use [Aspire local development](docs/localdev.md).
Install uv first; it creates `.venv` with Python 3.13 automatically. Aspire preserves
the extra development tools when synchronizing the locked runtime dependencies.
See [dependency maintenance](docs/localdev.md#updating-python-dependencies) before changing Python packages.

Install the pre-commit hooks:

```shell
pre-commit install
```

Compile the JavaScript:

```shell
( cd ./app/frontend ; npm install ; npm run build )
```

## Running unit tests

Run the tests:

```shell
python -m pytest
```

If test snapshots need updating (and the changes are expected), you can update them by running:

```shell
python -m pytest --snapshot-update
```

Once tests are passing, generate a coverage report to make sure your changes are covered:

```shell
pytest --cov --cov-report=xml && \
diff-cover coverage.xml --html-report coverage_report.html && \
open coverage_report.html
```

## Running E2E tests

Install Playwright browser dependencies:

```shell
playwright install --with-deps
```

Run the tests:

```shell
python -m pytest tests/e2e.py --tracing=retain-on-failure
```

When a failure happens, the trace zip will be saved in the test-results folder.
You can view that using the Playwright CLI:

```shell
playwright show-trace test-results/<trace-zip>
```

You can also use the online trace viewer at <https://trace.playwright.dev/>

## Code style

This codebase includes TypeScript, Python, PowerShell, and Bash.
Code should follow the standard conventions of each language.

For Python, you can enforce the conventions using `ruff` and `black`.

Install the development dependencies:

```shell
uv pip install -r requirements-dev.txt
```

Run `ruff` to lint a file:

```shell
python -m ruff <path-to-file>
```

Run `black` to format a file:

```shell
python -m black <path-to-file>
```

If you followed the steps above to install the pre-commit hooks, then you can just wait for those hooks to run `ruff` and `black` for you.

## Adding new features

We recommend using GitHub Copilot Agent mode when adding new features,
as this project includes an [AGENTS.md](AGENTS.md) file
that instructs Copilot (and other coding agents) about how to generate code for common code changes.

If you are not using Copilot Agent mode, consult both that file and suggestions below.

### Adding environment variables

Model service dependencies and deployment choices directly in `apphost.mts`.
Wire resource outputs to the backend's existing environment contract rather than
adding provider switches, environment forwarding loops, or `.env` loading to the
AppHost. Document explicit application-model changes in the relevant feature guide.
`.env.example` is for standalone ingestion/admin utilities only; their shell values
take precedence over `.env`. Do not add AZD state or deployment hooks.

### Adding new UI strings

When adding new UI strings, please remember to update all translations.
For any translations that you generate with an AI tool,
please indicate in the PR description which language's strings were AI-generated.

Here are community contributors that can review translations:

| Language | Contributor         |
|----------|---------------------|
| Danish   | @EMjetrot           |
| French   | @manekinekko        |
| Japanese | @bnodir             |
| Norwegian| @@jeannotdamoiseaux |
| Portugese| @glaucia86          |
| Spanish  | @miguelmsft         |
| Turkish  | @mertcakdogan       |
| Italian  | @ivanvaccarics      |
| Dutch    |                     |
| Polish   | @michuhu            |
