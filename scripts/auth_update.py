import asyncio
import os

from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv
from msgraph import GraphServiceClient
from msgraph.generated.models.application import Application
from msgraph.generated.models.spa_application import SpaApplication
from msgraph.generated.models.web_application import WebApplication

from auth_common import get_application, test_authentication_enabled


async def main():
    load_dotenv(override=False)
    if not test_authentication_enabled():
        print("Not updating authentication.")
        exit(0)

    auth_tenant = (os.getenv("AZURE_AUTH_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "").strip()
    credential = AzureCliCredential(tenant_id=auth_tenant)

    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

    frontend_uri = os.environ["FRONTEND_URI"].rstrip("/")
    backend_uri = os.getenv("BACKEND_URI", "").rstrip("/")
    client_app_id = os.getenv("AZURE_CLIENT_APP_ID", None)
    if client_app_id:
        client_object_id = await get_application(graph_client, client_app_id)
        if client_object_id:
            print(f"Updating redirect URIs for client app ID {client_app_id}...")
            existing = await graph_client.applications.by_application_id(client_object_id).get()
            if existing is None:
                raise ValueError("Client application was not found while updating redirect URIs")
            spa_redirects = list(existing.spa.redirect_uris or []) if existing.spa else []
            web_redirects = list(existing.web.redirect_uris or []) if existing.web else []
            frontend_redirect = f"{frontend_uri}/redirect"
            if frontend_redirect not in spa_redirects:
                spa_redirects.append(frontend_redirect)
            backend_redirect = f"{backend_uri}/.auth/login/aad/callback"
            if backend_uri and backend_redirect not in web_redirects:
                web_redirects.append(backend_redirect)
            # The local browser origin belongs to Vite, not the backend process.
            app = Application(
                spa=SpaApplication(redirect_uris=spa_redirects),
                web=WebApplication(redirect_uris=web_redirects),
            )
            await graph_client.applications.by_application_id(client_object_id).patch(app)
            print(f"Application update for client app id {client_app_id} complete.")


if __name__ == "__main__":
    asyncio.run(main())
