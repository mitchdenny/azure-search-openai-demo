from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from msgraph.generated.models.application import Application
from msgraph.generated.models.spa_application import SpaApplication
from msgraph.generated.models.web_application import WebApplication

from scripts import auth_update


@pytest.mark.asyncio
@pytest.mark.parametrize("backend_uri", ["", "https://hosted.example"])
async def test_update_keeps_existing_redirects(monkeypatch, backend_uri):
    monkeypatch.setattr(auth_update, "load_dotenv", lambda **kwargs: None)
    monkeypatch.setattr(auth_update, "test_authentication_enabled", lambda: True)
    monkeypatch.setattr(auth_update, "AzureCliCredential", MagicMock())
    monkeypatch.setattr(auth_update, "get_application", AsyncMock(return_value="client-object"))
    monkeypatch.setenv("AZURE_CLIENT_APP_ID", "client-app")
    monkeypatch.setenv("FRONTEND_URI", "http://localhost:54321/")
    monkeypatch.setenv("BACKEND_URI", backend_uri)
    existing = Application(
        spa=SpaApplication(redirect_uris=["https://other.example/redirect"]),
        web=WebApplication(redirect_uris=["https://other.example/.auth/login/aad/callback"]),
    )
    application = SimpleNamespace(get=AsyncMock(return_value=existing), patch=AsyncMock())
    client = MagicMock()
    client.applications.by_application_id.return_value = application
    monkeypatch.setattr(auth_update, "GraphServiceClient", MagicMock(return_value=client))

    await auth_update.main()

    updated = application.patch.call_args.args[0]
    assert updated.spa.redirect_uris == ["https://other.example/redirect", "http://localhost:54321/redirect"]
    assert "https://other.example/.auth/login/aad/callback" in updated.web.redirect_uris
    assert len(updated.web.redirect_uris) == (2 if backend_uri else 1)
    assert updated.public_client is None
