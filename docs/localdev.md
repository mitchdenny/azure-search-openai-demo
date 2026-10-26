# Local development with Aspire

## Azure resources in the app model

`apphost.mts` declares Azure Storage and its `content` Blob container, Azure AI Search,
and Azure OpenAI with `chat` (GPT-4.1 mini, version 2025-04-14) and `embeddings`
(text-embedding-3-small, version 1, 1536 dimensions) deployments. The backend receives
resource outputs and fixed application settings from that model. There is no AppHost
`.env` loader, provider selector, environment forwarding loop, or required-value schema.
Change resources/models in the AppHost rather than configuring alternate providers.

**Startup can provision billable Azure resources and role assignments.** Obtain
authorization first. Aspire asks for Azure subscription and location; select a region
with quota for both models. There is no AI Search emulator, and an empty index cannot
answer sample questions. Model calls and ingestion can incur charges.
See [Aspire local Azure provisioning](https://aspire.dev/integrations/cloud/azure/local-provisioning/)
for subscription/location configuration and provisioning permissions.

For keyless access, run `az login`.
The backend and utilities use `AzureCliCredential` locally and the backend keeps
`ManagedIdentityCredential` when `RUNNING_IN_PRODUCTION` or `WEBSITE_HOSTNAME` is set.
AppHost references declare resource access. If access is managed separately, the backend needs Search Index Data Reader
for queries, Storage Blob Data Reader for citations, and Cognitive Services OpenAI User
for models. Ingestion additionally needs Search Service Contributor, Search Index Data
Contributor, and Storage Blob Data Contributor. Optional services need their own roles.
Do not run role-assignment or app-registration utilities without authorization.

`.env` is only for standalone ingestion/admin utilities, not application startup.
It is ignored by Git and excluded from template output. Never put credentials in
`aspire.config.json`, command-line arguments, or committed files.

The upstream optional-feature implementation remains in the backend, but the template
does not expose its provider/feature matrix as parameters. Enabling an optional feature
requires explicit resource declarations and backend wiring in the AppHost.

## Setup and lifecycle

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) alongside Aspire,
Node.js and Azure CLI first. A separate Python installation is optional.
From the repository or generated application's root:

```sh
npm ci
npm --prefix app/frontend ci
az login
aspire restore
# Only after Azure provisioning and role assignments are authorized:
aspire start --non-interactive --isolated --apphost apphost.mts
aspire wait backend --apphost apphost.mts
aspire wait frontend --apphost apphost.mts
aspire describe --apphost apphost.mts
```

The same setup works on Windows; no manual virtual-environment creation is required.
Alternatively use foreground `aspire run --isolated --apphost apphost.mts`. Stop only this app:

```sh
aspire stop --non-interactive --apphost apphost.mts
```

The graph is `frontend (Vite) -> backend (Uvicorn/Quart) -> Storage, Search, OpenAI`,
plus an explicitly started `ingest` Python job targeting the same Azure resources.
Resource references and waits make the dependencies visible in the dashboard.
The backend uses `CHAT_URI` from the chat deployment reference as the Azure OpenAI
endpoint. Azure's endpoint hostname can differ from the resource name; do not
reconstruct it from `AZURE_OPENAI_SERVICE`.
AppHost/frontend use their own npm lockfiles. Aspire's native uv backend installer
runs `uv sync --locked --inexact --project ../.. --python 3.13 --default-index https://pypi.org/simple`
from `app/backend`. It creates the root `.venv`, installs `uv.lock`, and finishes before
the backend starts. The ingestion resource reuses that environment without a second install.
`--inexact` preserves separately installed development tools while enforcing locked runtime
versions. No `pip` executable is required in the environment.
The project metadata and `.python-version` select Python 3.13. uv uses a compatible
installation or automatically downloads one, rather than using an arbitrary system
Python. First startup therefore requires network access for packages and possibly Python.
The installer explicitly selects public PyPI instead of an inherited stale index; it
does not change machine-wide package-manager configuration.
Do not edit generated `.aspire/modules`.

Vite and Uvicorn ports are assigned by Aspire. Vite receives `BACKEND_URL` from the
backend endpoint and proxies API requests, preserving one browser origin for authentication,
uploads and citations. Both services use loopback HTTP locally. The dashboard has its own
HTTPS configuration; generated copies receive new dashboard ports. In the same source
checkout, dashboard profile ports can be adjusted in `aspire.config.json` if necessary.
Python reload and Vite HMR are enabled. Changing AppHost/configuration requires restarting it.

### Installer failures after changing Python

Updating the system Python does not update an existing virtual environment.
Verify `.venv/bin/python --version` (Windows: `.venv\Scripts\python.exe --version`).
The pinned native dependencies are tested on Python 3.13; on Python 3.15,
`jiter` and `tiktoken` can fail to build because their PyO3 versions do not support
that interpreter. Do not bypass PyO3's compatibility checks.

Stop this app before changing an environment used by running Python resources.
uv replaces an incompatible `.venv` with a Python 3.13 environment on startup.
Move the old environment aside first if you need to preserve its contents.
If Python downloads are disabled by machine policy, install Python 3.13 separately
or run `uv python install 3.13` with the required network access. Do not force uv to
use an unsupported interpreter. A stale nested `app/backend/.venv` is not used.

### Updating Python dependencies

Keep direct requirements in `app/backend/requirements.in` and the root project's
`dependencies` synchronized. The tests check that these declarations agree.
`app/backend/requirements.txt` remains the pinned compatibility input for standalone
tools and cloud Functions. After intentionally editing requirements, compile it from
`app/backend` using `uv pip compile requirements.in -o requirements.txt --python-version 3.10`.
Then update the root project and uv lock without changing an active environment:

```sh
uv add --raw --no-sync -r app/backend/requirements.in -c app/backend/requirements.txt \
  --default-index https://pypi.org/simple --python 3.13
```

When removing a dependency, remove it from both direct declarations before regenerating.
Use `--upgrade-package <package>` only for an intentional upgrade. Commit both lockfiles.

## Ingest documents explicitly

After authorized provisioning, start **ingest** from the Aspire dashboard, or from
another terminal at the application root:

```sh
aspire resource ingest start --apphost apphost.mts
aspire logs ingest --apphost apphost.mts
```

The resource waits for the backend to be healthy so its shared Python environment
and dependencies are ready. It uploads `data/`, creates/populates `gptkbindex`, uses
local PDF/HTML parsing and real embeddings, and exits when finished. It receives
Storage, Search and OpenAI settings directly from AppHost outputs and ignores `.env`.
Wait for a terminal state (such as **Finished**) with **exit code 0**, not just a
successful Start command.
The first ingestion can take tens of minutes with low embedding quotas; watch its
console logs and prepare data before presenting the demo.

`ingest` uses `withExplicitStart()`: app startup/restart does not run it or trigger
paid embedding calls. Start it explicitly after a restart when new/changed data needs
uploading. Reruns skip unchanged files; hashes are recorded only after successful
processing so failed files can be retried. The backend/frontend remain available
while ingestion runs, but sample questions need the corresponding documents indexed.

For a standalone utility invocation instead, copy `.env.example` to `.env` for the
ingestion utility and fill in the actual Storage, Search and OpenAI account names
from the provisioned resources. Set `AZURE_OPENAI_ENDPOINT` to the actual endpoint
shown as `CHAT_URI` in the backend resource's environment in the Aspire dashboard,
for example `https://<actual-subdomain>.openai.azure.com/`. Do not infer the endpoint
from the resource name. Keep `OPENAI_HOST=azure` from the example.
The deployment, index and container defaults match
the AppHost. Do not change embedding model/dimensions independently of the index.
With Azure access, data mutation and model usage authorized:

```sh
.venv/bin/python app/backend/prepdocs.py 'data/*' --verbose
```

The shell/PowerShell `scripts/prepdocs` wrappers run the same command and preserve
additional arguments. Local PDF/HTML parsing is enabled in `.env.example`; it avoids
Document Intelligence but can lose advanced layout/image extraction. For full extraction
provide `AZURE_DOCUMENTINTELLIGENCE_SERVICE` and disable the corresponding local parser.
Embeddings still call a real model. Use a fresh index/container for experiments.
Both paths can create/update an index and upload content; neither runs automatically.
Wait for ingestion to finish successfully before asking the sample questions.
Resource-group/subscription values are optional for this local ingestion path;
Azure CLI supplies the signed-in identity.
MD5 sidecars are shared across configurations, so remove only the relevant `data/*.md5`
files when deliberately ingesting unchanged documents into a new target.
See [ingestion architecture and options](data_ingestion.md).

If chat reports `ResourceNotFoundError` and backend logs say
`The index 'gptkbindex' ... was not found`, the Search service exists but ingestion
has not created the index. This is not an OpenAI model compatibility failure.
Complete the authorized ingestion above; restarting the backend or retrying the chat
does not create the index. A streamed chat request can return HTTP 200 with an error
event in its body, so inspect the UI and downstream Search spans, not just HTTP status.

Cloud ingestion remains optional: configure separately deployed Functions, run
`python scripts/copy_prepdocslib.py`, and invoke
`python app/backend/setup_cloud_ingestion.py` explicitly with the necessary environment.
The AppHost does not provision or host those Functions.

## Verification and limits

`/health` reports process readiness after Quart client initialization. `/config`
and `/auth_setup` can confirm frontend proxying without model usage.
**Healthy does not mean Azure credentials, index contents, or models have been tested.**
With approved real configuration, ask a question about the ingested sample documents,
confirm streamed answer text and citations, and open a citation to check Blob access.
Do not claim functional RAG verification from a rendered UI or a mocked test.
See [authentication](login_and_acl.md) for separate Entra/OBO verification.

## Tests

```sh
uv sync --locked --default-index https://pypi.org/simple
source .venv/bin/activate
uv pip install -r requirements-dev.txt
npm --prefix app/frontend run build
pytest tests/
ruff check .
ty check
npm run build
```

Tests mock external Azure services. E2E tests additionally require Playwright Chromium:
`playwright install chromium` then `pytest tests/e2e.py`. Build the frontend first
because these tests serve its compiled assets from Quart. Live model/Entra validation
is a separate authorized step, not part of the mocked suite.
