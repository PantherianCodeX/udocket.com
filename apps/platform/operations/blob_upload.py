from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from django.conf import settings
import logging

log = logging.getLogger("apps.platform.operations.blob")


def _parse_conn_string(cs: str) -> dict[str, str]:
    parts = [p for p in cs.split(";") if p]
    kv: dict[str, str] = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv


def upload_with_sas(local_file: Path, case_id: str, job_id: str, original_name: Optional[str] = None) -> str:
    from azure.storage.blob import (
        BlobServiceClient,
        ContentSettings,
        generate_blob_sas,
        BlobSasPermissions,
    )
    from azure.core.exceptions import HttpResponseError

    container = getattr(settings, "AZURE_BLOB_CONTAINER", None)
    if not container:
        raise RuntimeError("AZURE_BLOB_CONTAINER is not configured")

    original = original_name or local_file.name
    blob_name = f"cases/{case_id}/audio/{job_id}__{original}"

    conn_str = getattr(settings, "AZURE_BLOB_CONNECTION_STRING", None)
    account = getattr(settings, "AZURE_BLOB_ACCOUNT", None)
    key = getattr(settings, "AZURE_BLOB_KEY", None)

    if conn_str:
        svc = BlobServiceClient.from_connection_string(conn_str)
    else:
        if not account or not key:
            raise RuntimeError("Missing Azure Blob credentials (AZURE_BLOB_ACCOUNT/AZURE_BLOB_KEY or connection string)")
        account_url = f"https://{account}.blob.core.windows.net"
        svc = BlobServiceClient(account_url=account_url, credential=key)
    log.info("blob: preparing upload", extra={"container": container, "blob": blob_name})

    container_client = svc.get_container_client(container)
    try:
        container_client.create_container()
    except Exception:
        pass

    def _guess_content_type(filename: str) -> str:
        low = filename.lower()
        if low.endswith(".wav"):
            return "audio/wav"
        if low.endswith(".mp3"):
            return "audio/mpeg"
        if low.endswith(".m4a"):
            return "audio/mp4"
        if low.endswith(".flac"):
            return "audio/flac"
        if low.endswith(".ogg"):
            return "audio/ogg"
        if low.endswith(".aac"):
            return "audio/aac"
        return "application/octet-stream"

    blob_client = container_client.get_blob_client(blob_name)
    content_settings = ContentSettings(content_type=_guess_content_type(original))
    try:
        with open(local_file, "rb") as f:
            blob_client.upload_blob(f, overwrite=True, content_settings=content_settings)
    except HttpResponseError as e:  # pragma: no cover - passthrough
        raise RuntimeError(
            "Azure Blob upload failed: AuthorizationFailure or insufficient permissions. "
            "Verify AZURE_BLOB_* credentials and container access. Original: " + (e.message if hasattr(e, "message") else str(e))
        )
    log.info("blob: uploaded", extra={"container": container, "blob": blob_name})

    # Try to reuse SAS from connection string if present
    url_with_possible_sas = getattr(blob_client, "url", None)
    if isinstance(url_with_possible_sas, str) and "?" in url_with_possible_sas:
        return url_with_possible_sas

    # Else sign a SAS
    endpoint_suffix = "blob.core.windows.net"
    blob_endpoint = None
    if conn_str:
        kv = _parse_conn_string(conn_str)
        account_name = kv.get("AccountName") or account
        key = kv.get("AccountKey") or key
        if kv.get("EndpointSuffix"):
            endpoint_suffix = f"blob.{kv['EndpointSuffix']}"
        blob_endpoint = kv.get("BlobEndpoint")
    else:
        account_name = account

    if not account_name or not key:
        raise RuntimeError("Missing account key for SAS signing (set AZURE_BLOB_KEY or include AccountKey in connection string)")

    sas = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=int(getattr(settings, "AZURE_BLOB_SAS_TTL_MIN", 120))),
    )
    base = blob_endpoint or f"https://{account_name}.{endpoint_suffix}"
    url = f"{base}/{container}/{blob_name}?{sas}"
    log.info("blob: sas generated", extra={"url_prefix": url.split("?",1)[0]})
    return url
