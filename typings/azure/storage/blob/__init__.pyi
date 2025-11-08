from __future__ import annotations

from typing import Any, Iterable, Protocol

from datetime import datetime


class BlobBlock:
    def __init__(self, *, block_id: str) -> None: ...


class BlobSasPermissions:
    def __init__(self, **permissions: bool) -> None: ...


class ContentSettings:
    def __init__(self, content_type: str | None = ..., **kwargs) -> None: ...


class BlobClient(Protocol):
    url: str

    def stage_block(self, *, block_id: str, data: bytes) -> None: ...

    def commit_block_list(self, blocks: Iterable[BlobBlock]) -> None: ...

    def set_http_headers(self, **kwargs: Any) -> None: ...

    def delete_blob(self) -> None: ...


class ContainerClient(Protocol):
    def create_container(self) -> None: ...

    def get_blob_client(self, blob: str) -> BlobClient: ...


class BlobServiceClient:
    @classmethod
    def from_connection_string(cls, conn_str: str) -> BlobServiceClient: ...

    def __init__(self, *, account_url: str | None = ..., credential: Any = ...) -> None: ...

    def get_container_client(self, container: str) -> ContainerClient: ...


def generate_blob_sas(
    *,
    account_name: str,
    container_name: str,
    blob_name: str,
    account_key: str,
    permission: BlobSasPermissions,
    expiry: datetime,
) -> str: ...
