# Production considerations

This template currently implements the local Aspire inner loop only. A future
`aspire deploy` target must explicitly model compute, networking, identity, service
static assets/reverse proxying, secrets, and cloud ingestion Functions.
Storage, Search and OpenAI resource provisioning is already declared in the AppHost.
The removed AZD/Bicep setup is not an implicit deployment fallback.

Retain the original application's production requirements: managed identity with
least-privilege access, Entra login and ACL enforcement where required, private
network connectivity, appropriate Search tier/replicas, model quota, Storage
redundancy, persistence/retention, content safety, and real authentication tests.
Use the optional Cosmos history, speech, multimodal, user-upload, and agentic
settings only with separately provisioned services and correct permissions.

Local loopback HTTP and process-only health checks are development choices, not a
production security or availability design. Cloud runtime must serve the compiled
frontend (including the dedicated MSAL redirect bridge), implement TLS, and validate
service connectivity independently. See the [upstream production guide](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/docs/productionizing.md)
for additional service-sizing considerations; its deployment commands do not apply.
