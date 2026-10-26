# Monitoring

Aspire collects backend OpenTelemetry traces when `OTEL_EXPORTER_OTLP_ENDPOINT` is
injected. ASGI, HTTPX, aiohttp and OpenAI instrumentation cover API requests and
outgoing retrieval/model operations. The dashboard also shows process logs,
resource health, endpoints and dependency relationships.

Open the dashboard URL printed by `aspire start` or `aspire run`.
Use `aspire describe --apphost apphost.mts` for resource state and the dashboard
for traces/logs. Never publish the dashboard login token or unredacted secrets.

Existing Azure Monitor behavior is retained: when
`APPLICATIONINSIGHTS_CONNECTION_STRING` is set, `configure_azure_monitor` is used
instead of the local OTLP provider. This avoids registering two competing trace
providers. Azure Monitor resources are not provisioned by this template.
The standalone OTLP path currently exports traces, not a separate metrics/logs SDK
pipeline. Console logs remain visible through Aspire.

`GET /health` checks process readiness only, not external Azure access.
Search/model requests may be billed; do not use them as periodic health probes.
The browser-logging integration is not enabled because it is not available at the
template's stable 13.6.4 package version.
