# What this template brings together

This Aspire template models a document-grounded chat application: a browser asks
questions, a Python API retrieves relevant document sections, and an Azure OpenAI
model uses that context to answer with citations. The TypeScript AppHost is the
resource graph connecting those pieces, rather than a second application
configuration system.

## The application and its knowledge

- **Frontend:** a Vite React application provides the chat experience. It owns
  the browser origin and proxies API requests to the backend, keeping cookies and
  authentication redirects same-origin.
- **Backend:** Uvicorn runs the Quart retrieval-augmented generation (RAG) API.
  It combines search results with chat prompts and serves document citations.
- **Azure Blob Storage:** the `content` container holds source documents used
  for ingestion and citation access.
- **Azure AI Search:** the `gptkbindex` index holds searchable document sections
  and embeddings so the backend can retrieve grounding material.
- **Azure OpenAI:** the `chat` deployment uses `gpt-4.1-mini` to generate answers;
  the `embeddings` deployment uses `text-embedding-3-small` to represent document
  sections and queries for vector retrieval.

The AppHost declares these Azure resources and model deployments, then passes
their outputs and references to consumers. Aspire assigns local endpoints and
orders startup around resource dependencies instead of relying on fixed ports.

## Preparing the sample knowledge

An `ingest` resource starts automatically after the backend becomes healthy. It
processes the bundled sample data, uploads documents to Blob Storage, and indexes
their sections and embeddings in Search. Remote Blob completion fingerprints
and the presence of all expected Search section IDs let it skip unchanged,
successfully completed files; a local cache alone is not proof of completion.

The backend owns the uv-managed Python 3.13 environment at the repository root.
Ingestion shares that environment without running a separate dependency install.
Frontend readiness does not mean ingestion has finished or every document is
already searchable.

## Visibility and operational boundaries

Aspire brings resource state, endpoints, logs, and available telemetry together
in its dashboard. HTTP health checks cover the backend's `/health` endpoint and
the frontend's `/` endpoint. These indicate process readiness, not successful
Azure authentication, a populated index, or working model access.

This is not an all-local emulator stack. Starting the AppHost can provision real
Azure services and role assignments, automatically upload and index documents,
and make billable embedding calls. Chat and query embedding requests can also
incur model charges. Startup therefore requires authorization for those effects
and suitable Azure credentials; local development uses Azure sign-in rather
than embedded secrets.

The template currently focuses on this local orchestration experience backed by
Azure services. A cloud application deployment target remains future work.
