"""Graph credential acquisition.

Priority order (each falls back only if the previous is not configured):

1. Managed Identity (system- or user-assigned) when ``USE_MANAGED_IDENTITY=true``.
2. Certificate auth when ``AZURE_CLIENT_CERTIFICATE_PATH`` is set.
3. Client secret retrieved from Key Vault when
   ``AZURE_CLIENT_SECRET_KEYVAULT_URI`` is set.
4. Inline client secret from ``AZURE_CLIENT_SECRET`` (least preferred).

All paths return a Graph access token string or ``None`` on failure.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import msal

from config import settings

logger = logging.getLogger("credentials")


def _load_certificate() -> Optional[dict]:
    if not settings.azure_client_certificate_path:
        return None
    path = Path(settings.azure_client_certificate_path)
    if not path.is_file():
        logger.error("Certificate path not found: %s", path)
        return None
    private_key = path.read_text(encoding="utf-8")
    return {
        "private_key": private_key,
        "thumbprint": settings.azure_client_certificate_thumbprint,
    }


def _secret_from_keyvault() -> Optional[str]:
    uri = settings.azure_client_secret_keyvault_uri
    if not uri:
        return None
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        # Expect URI of the form: https://<vault>.vault.azure.net/secrets/<name>
        parts = uri.rstrip("/").split("/")
        vault_url = "/".join(parts[:3])
        secret_name = parts[-1]
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        return client.get_secret(secret_name).value
    except Exception as exc:
        logger.error("Failed to fetch secret from Key Vault: %s", exc)
        return None


def get_graph_token(scope: Optional[str] = None) -> Optional[str]:
    """Acquire an app-only Graph token using the best available credential."""
    scope = scope or settings.graph_scope

    # 1) Managed Identity
    if settings.use_managed_identity:
        try:
            from azure.identity import ManagedIdentityCredential
            kwargs = {}
            if settings.managed_identity_client_id:
                kwargs["client_id"] = settings.managed_identity_client_id
            credential = ManagedIdentityCredential(**kwargs)
            return credential.get_token(scope).token
        except Exception as exc:
            logger.error("Managed Identity token acquisition failed: %s", exc)
            return None

    # 2) Certificate
    cert = _load_certificate()
    if cert:
        app = msal.ConfidentialClientApplication(
            client_id=settings.azure_client_id,
            client_credential=cert,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        )
        result = app.acquire_token_for_client(scopes=[scope])
        if "access_token" in result:
            return result["access_token"]
        logger.error("Certificate auth failed: %s", result.get("error_description"))
        return None

    # 3) Secret from Key Vault or inline
    secret = _secret_from_keyvault() or settings.azure_client_secret
    if not secret:
        logger.error("No credential configured (MI / cert / secret all empty)")
        return None
    app = msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=secret,
        authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=[scope])
    if "access_token" in result:
        return result["access_token"]
    logger.error("Secret auth failed: %s", result.get("error_description"))
    return None
