# Authentication and document access control

The original Entra/MSAL authentication, on-behalf-of (OBO) token exchange, ACL filters,
user uploads, and Cosmos history code is retained. Aspire does not create app
registrations or configure hosted Easy Auth. Azure service references in the AppHost
can provision service-access role assignments, which are separate from Entra app registration.

Authentication is not a template switch. To enable it, explicitly wire the settings
below to the backend with `.withEnvironment(...)` in `apphost.mts`, using a secret
Aspire parameter for the server secret. The backend does not load root `.env`:

```dotenv
AZURE_USE_AUTHENTICATION=true
AZURE_ENFORCE_ACCESS_CONTROL=true
AZURE_ENABLE_UNAUTHENTICATED_ACCESS=false
AZURE_AUTH_TENANT_ID=<tenant-id>
AZURE_CLIENT_APP_ID=<client-app-id>
AZURE_SERVER_APP_ID=<server-app-id>
AZURE_SERVER_APP_SECRET=<secret>
```

Keep secrets local. Configure API permissions, consent and Search/Storage access
separately. The server app must expose the delegated API scope and accept the client
app, and the client needs that scope and the relevant delegated Search permissions.
See [upstream setup details](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/docs/login_and_acl.md)
for Entra registration and ACL concepts, **not** its obsolete AZD commands.

Get the frontend URL from `aspire describe --apphost apphost.mts`.
Register `<frontend-url>/redirect` as an SPA redirect URI in Entra. This must target
the frontend origin, not the internal backend port. Vite serves the dedicated
`redirect.html` bridge via `/redirect`; do not replace it with the SPA or a blank page.
Dynamic ports can change between runs, so ensure the current loopback redirect is
accepted by your registration. Hosted Easy Auth redirect settings are separate.

Utilities remain available, but are **explicit administrative actions**:

* `python scripts/auth_init.py` creates/updates registrations and secrets, writing
  returned IDs/secrets to `.env` rather than AZD state.
* `FRONTEND_URI=<frontend-url> python scripts/auth_update.py` updates SPA redirects;
  optional `BACKEND_URI` adds hosted Easy Auth callbacks.
* `python scripts/manageacl.py --help` manages document ACLs.
* `python scripts/verify_search_index_acls.py` inspects index ACL configuration.
* Cloud ingestion ACLs and ADLS helpers are retained for existing infrastructure.

Never run these mutation utilities just to validate an inner loop.

## Live verification

Unit tests mock MSAL/Graph; passing them does not validate Entra.
With an authorized tenant and ACL-enabled index, sign in from the frontend,
confirm the popup closes, the toolbar shows the user, and a document ACL'd to that
user produces an answer with its citation. A document not ACL'd to the user must not
be returned. Log out and sign in again to test the redirect bridge a second time.
Check backend logs for OBO/token errors. Also test optional user uploads and
Cosmos history if enabled. Hosted Easy Auth requires a separate real deployment;
local MSAL popup success does not validate it.
