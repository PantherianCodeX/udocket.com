# pyright: strict

from __future__ import annotations

import base64
import logging
import re
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

from django.conf import settings

from packages.udocket_common.time import utc_now

log = logging.getLogger("apps.platform.operations.blob")


class UploadCancelled(RuntimeError):
    """Raised when an upload is cancelled mid-transfer."""

    pass


def _parse_conn_string(cs: str) -> dict[str, str]:
    parts = [segment for segment in cs.split(";") if segment]
    kv: dict[str, str] = {}
    for segment in parts:
        if "=" in segment:
            key, value = segment.split("=", 1)
            kv[key.strip()] = value.strip()
    return kv


def upload_with_sas(
    local_file: Path,
    case_id: str,
    job_id: str,
    *,
    organization_id: str | None = None,
    original_name: str | None = None,
    cancel_check: Callable[[], bool] | None = None,
    progress_cb: Callable[[float], None] | None = None,
) -> str:
    from azure.core.exceptions import HttpResponseError
    from azure.storage.blob import (
        BlobBlock,
        BlobSasPermissions,
        BlobServiceClient,
        ContentSettings,
        generate_blob_sas,
    )

    container = getattr(settings, "AZURE_BLOB_CONTAINER", None)
    if not container:
        raise RuntimeError("AZURE_BLOB_CONTAINER is not configured")

    original = original_name or local_file.name
    # Strip local naming prefix "<jobUUID>__" so the blob name avoids duplicating the job id.
    original = re.sub(r"^[0-9a-fA-F-]{36}__", "", original)
    safe_original = re.sub(r"[^A-Za-z0-9_.-]", "_", original)
    if not safe_original:
        safe_original = "audio"
    org_segment = organization_id or "unassigned"
    blob_name = f"tenants/{org_segment}/cases/{case_id}/audio/{job_id}__{safe_original}"

    conn_str = getattr(settings, "AZURE_BLOB_CONNECTION_STRING", None)
    account = getattr(settings, "AZURE_BLOB_ACCOUNT", None)
    key = getattr(settings, "AZURE_BLOB_KEY", None)

    if conn_str:
        svc = BlobServiceClient.from_connection_string(conn_str)
    else:
        if not account or not key:
            raise RuntimeError(
                "Missing Azure Blob credentials (AZURE_BLOB_ACCOUNT/AZURE_BLOB_KEY "
                "or connection string)"
            )
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
        try:
            blob_client.delete_blob()
        except Exception:
            pass
        chunk_size = 8 * 1024 * 1024  # 8 MiB
        block_ids: list[str] = []
        total = max(1, local_file.stat().st_size)
        uploaded = 0
        if progress_cb:
            progress_cb(0.0)
        with open(local_file, "rb") as handle:
            idx = 0
            while True:
                if cancel_check and cancel_check():
                    raise UploadCancelled("Upload cancelled")
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                block_id_raw = f"{idx:08d}".encode("ascii")
                block_id = base64.b64encode(block_id_raw).decode("ascii")
                blob_client.stage_block(block_id=block_id, data=chunk)
                block_ids.append(block_id)
                uploaded += len(chunk)
                idx += 1
                if progress_cb:
                    progress_cb(min(uploaded / total, 1.0))
        blob_client.commit_block_list([BlobBlock(block_id=b) for b in block_ids])
        try:
            blob_client.set_http_headers(content_settings=content_settings)
        except Exception:
            pass
        if progress_cb:
            progress_cb(1.0)
    except HttpResponseError as e:  # pragma: no cover - passthrough
        raise RuntimeError(
            "Azure Blob upload failed: AuthorizationFailure or insufficient permissions. "
            "Verify AZURE_BLOB_* credentials and container access. Original: "
            + (e.message if hasattr(e, "message") else str(e))
        )
    log.info("blob: uploaded", extra={"container": container, "blob": blob_name})

    # Try to reuse SAS from connection string if present
    url_with_possible_sas = getattr(blob_client, "url", None)
    if isinstance(url_with_possible_sas, str) and "?" in url_with_possible_sas:
        return url_with_possible_sas

    # Else sign a SAS
    endpoint_suffix = "blob.core.windows.net"
    blob_endpoint: str | None = None
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
        raise RuntimeError(
            "Missing account key for SAS signing (set AZURE_BLOB_KEY or include AccountKey "
            "in connection string)"
        )

    sas = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=key,
        permission=BlobSasPermissions(read=True),
        expiry=utc_now() + timedelta(minutes=int(getattr(settings, "AZURE_BLOB_SAS_TTL_MIN", 120))),
    )
    base = blob_endpoint or f"https://{account_name}.{endpoint_suffix}"
    safe_blob = quote(blob_name, safe="/:")
    url = f"{base}/{container}/{safe_blob}?{sas}"
    log.info("blob: sas generated", extra={"url_prefix": url.split("?", 1)[0]})
    return url
