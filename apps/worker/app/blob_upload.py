from __future__ import annotations
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
)
from azure.core.exceptions import HttpResponseError
from config.settings import settings


def _parse_conn_string(cs: str) -> dict[str, str]:
    parts = [p for p in cs.split(';') if p]
    kv = {}
    for p in parts:
        if '=' in p:
            k, v = p.split('=', 1)
            kv[k.strip()] = v.strip()
    return kv


def _service_client() -> BlobServiceClient:
    if settings.AZURE_BLOB_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(settings.AZURE_BLOB_CONNECTION_STRING)
    if not settings.AZURE_BLOB_ACCOUNT or not settings.AZURE_BLOB_KEY:
        raise RuntimeError("Missing Azure Blob credentials (AZURE_BLOB_ACCOUNT/AZURE_BLOB_KEY or connection string)")
    # Default endpoint suffix for public Azure; adjust if sovereign cloud is used
    account_url = f"https://{settings.AZURE_BLOB_ACCOUNT}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=settings.AZURE_BLOB_KEY)


def _guess_content_type(filename: str) -> str:
    low = filename.lower()
    if low.endswith('.wav'): return 'audio/wav'
    if low.endswith('.mp3'): return 'audio/mpeg'
    if low.endswith('.m4a'): return 'audio/mp4'
    if low.endswith('.flac'): return 'audio/flac'
    if low.endswith('.ogg'): return 'audio/ogg'
    if low.endswith('.aac'): return 'audio/aac'
    return 'application/octet-stream'


def upload_with_sas(local_file: Path, case_id: str, job_id: str, original_name: Optional[str] = None) -> str:
    if not settings.AZURE_BLOB_CONTAINER:
        raise RuntimeError("AZURE_BLOB_CONTAINER is not configured")

    original = original_name or local_file.name
    blob_name = f"cases/{case_id}/audio/{job_id}__{original}"

    svc = _service_client()
    container = settings.AZURE_BLOB_CONTAINER
    container_client = svc.get_container_client(container)
    try:
        container_client.create_container()
    except Exception:
        # already exists
        pass

    blob_client = container_client.get_blob_client(blob_name)
    content_settings = ContentSettings(content_type=_guess_content_type(original))
    try:
        with open(local_file, 'rb') as f:
            blob_client.upload_blob(f, overwrite=True, content_settings=content_settings)
    except HttpResponseError as e:
        raise RuntimeError(
            "Azure Blob upload failed: AuthorizationFailure or insufficient permissions. "
            "Verify AZURE_BLOB_* credentials and container access. Original: " + (e.message if hasattr(e, 'message') else str(e))
        )

    # Generate read-only SAS URL
    # If client is SAS-authenticated via connection string, its .url typically already includes the SAS
    url_with_possible_sas = getattr(blob_client, 'url', None)
    if isinstance(url_with_possible_sas, str) and '?' in url_with_possible_sas:
        return url_with_possible_sas

    # Else, sign a fresh SAS using account key
    account_name = None
    key = None
    endpoint_suffix = 'blob.core.windows.net'
    if settings.AZURE_BLOB_CONNECTION_STRING:
        kv = _parse_conn_string(settings.AZURE_BLOB_CONNECTION_STRING)
        account_name = kv.get('AccountName')
        key = kv.get('AccountKey') or settings.AZURE_BLOB_KEY
        if kv.get('EndpointSuffix'):
            endpoint_suffix = f"blob.{kv['EndpointSuffix']}"
        # Prefer explicit BlobEndpoint if present
        blob_endpoint = kv.get('BlobEndpoint')
    else:
        account_name = settings.AZURE_BLOB_ACCOUNT
        key = settings.AZURE_BLOB_KEY
        blob_endpoint = None

    if not account_name or not key:
        raise RuntimeError("Missing account key for SAS signing (set AZURE_BLOB_KEY or include AccountKey in connection string)")

    sas = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=settings.AZURE_BLOB_SAS_TTL_MIN),
    )
    base = blob_endpoint or f"https://{account_name}.{endpoint_suffix}"
    return f"{base}/{container}/{blob_name}?{sas}"
