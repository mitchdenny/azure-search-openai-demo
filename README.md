# SearchOpenAI Aspire template

An Aspire-orchestrated Python/React retrieval-augmented chat application, adapted from
[Azure-Samples/azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo).
The original MIT license, sample documents, application features, and tests are retained.

The TypeScript AppHost runs the Quart backend and Vite frontend with managed ports,
same-origin API proxying, hot reload, health checks, and backend OpenTelemetry traces.
It models Azure Storage, Azure AI Search, and Azure OpenAI chat/embedding deployments
directly in the AppHost; Azure AI Search has no faithful local emulator.
This is not an offline demo and does not replace real model/retrieval calls with mock responses.

## Run locally

Install Aspire 13.6.4+, Node.js 22.13+ (or 24+), [uv](https://docs.astral.sh/uv/getting-started/installation/),
and Azure CLI. uv selects or downloads Python 3.13; you do not need to create a virtual
environment or change your system Python.

```sh
npm ci
npm --prefix app/frontend ci
az login
aspire restore
aspire run --isolated --apphost apphost.mts
```

Aspire's backend installer creates the root `.venv` and installs `uv.lock` from public
PyPI before starting the backend. Ingestion reuses that environment. Python is constrained
to 3.13, regardless of newer or older system interpreters. First startup needs network
access for packages and, if necessary, the Python download.
Startup uses Aspire's Azure subscription/location configuration and can provision
billable resources and role assignments, upload documents and make paid embedding
calls. Run it only with authorization for these effects.
The template uses GPT-4.1 mini and text-embedding-3-small (1536 dimensions).
Change the resource declarations in `apphost.mts`, not a set of provider environment variables.
Open the frontend URL in the Aspire dashboard. No frontend build is required for development.
The **ingest** resource automatically prepares `data/` after the backend is healthy.
**Before asking sample questions, wait for [ingest to finish successfully](docs/localdev.md#automatic-document-ingestion).**
Watch progress from the dashboard or another terminal:

```sh
aspire logs ingest --apphost apphost.mts
```

It uses the AppHost's Azure resources, with no `.env` setup. On subsequent starts it
checks Azure Blob completion metadata and Search sections, skipping unchanged,
successfully ingested files without uploading or embedding them again. Missing or
changed files are processed; failures remain visible in the resource logs and can be retried.
Prepare data before a demo: initial PDF ingestion can take tens of minutes at low
embedding quotas. Existing documents without completion metadata are ingested once
to establish a reliable checkpoint.
See [local development](docs/localdev.md) for prerequisites, permissions, ingestion,
authentication, troubleshooting, and the limits of health checks.

## Create an application from the template

Custom directory/Git sources require the Aspire CLI feature from
[microsoft/aspire#21263](https://github.com/microsoft/aspire/pull/21263);
the released 13.6.4 CLI does not support these options.
Use a feature-enabled CLI as `aspire` in the following commands:

```sh
aspire new --template-path . --name MySearchChat --output ../MySearchChat \
  --suppress-agent-init --non-interactive
```

Or use the fork and a reviewed **full commit SHA**:

```sh
aspire new --template-repository https://github.com/mitchdenny/azure-search-openai-demo \
  --template-repository-ref <full-commit-sha> --template-path . \
  --name MySearchChat --output ../MySearchChat --suppress-agent-init --non-interactive
```

Generation does **not** restore dependencies, run scripts, ingest data, or provision Azure.
Run the local setup commands inside the generated directory. Names and dashboard ports
are generated; secrets, caches, generated modules, Git metadata, and installed packages
are excluded. `AspireVersion` receives the generating CLI's SDK identity; hosting
integration versions resolve independently through its NuGet package policy.
For a PR CLI, use its documented `ASPIRE_CLI_PACKAGES` override with matching packages.
There are no PR-specific dependencies or machine-local feed paths in this template.
Ordinary .NET template-engine generation uses stable 13.6.4 defaults.

## Scope

AZD manifests, Bicep provisioning, AZD deployment workflows/hooks, and obsolete startup
scripts have been removed. The intended deployment direction is `aspire deploy`, but
**this change does not yet implement a cloud deployment target**. Do not treat a local
startup as proof that cloud provisioning, hosted authentication, or live retrieval works.
Cloud ingestion Functions and setup utilities remain available for separately managed
infrastructure; the AppHost does not deploy or automatically run them.

See the [documentation index](docs/README.md) and [contributing guide](CONTRIBUTING.md).
