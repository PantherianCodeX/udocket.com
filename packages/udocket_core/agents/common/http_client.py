from __future__ import annotations

# pyright: strict

"""Wrapper utilities around ``requests`` session pooling for Azure clients."""

import threading
from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol, cast

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class _RequestsResponseProtocol(Protocol):
    status_code: int
    text: str
    headers: Mapping[str, object] | None

    def json(self) -> object: ...

    def iter_lines(self, decode_unicode: bool | None = None) -> Iterable[str | bytes]: ...


class _RequestsSessionProtocol(Protocol):
    def post(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        json: object | None = None,
        stream: bool | None = None,
        timeout: int | float | tuple[float, float] | None = None,
    ) -> _RequestsResponseProtocol: ...

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | float | tuple[float, float] | None = None,
    ) -> _RequestsResponseProtocol: ...

    def close(self) -> None: ...

    def mount(self, prefix: str, adapter: object) -> None: ...


class _RequestsModuleProtocol(Protocol):
    class exceptions(Protocol):
        HTTPError: type[Exception]
        RequestException: type[Exception]

    Session: type[_RequestsSessionProtocol]


_REQUESTS: _RequestsModuleProtocol = cast(_RequestsModuleProtocol, requests)
_HTTP_ADAPTER_CLS = HTTPAdapter
_RETRY_CLS = Retry


@dataclass(frozen=True)
class HTTPRetryConfig:
    total: int = 3
    backoff_factor: float = 0.5
    status_forcelist: tuple[int, ...] = (
        408,
        409,
        425,
        429,
        500,
        502,
        503,
        504,
        521,
        522,
        524,
    )
    allowed_methods: tuple[str, ...] = ("HEAD", "GET", "OPTIONS", "POST")
    respect_retry_after_header: bool = True


@dataclass(frozen=True)
class HTTPSessionConfig:
    pool_maxsize: int = 10
    retry: HTTPRetryConfig = HTTPRetryConfig()


class RequestsSessionManager:
    """Shared pool of configured requests.Session instances keyed by endpoint."""

    def __init__(self, *, config: HTTPSessionConfig | None = None) -> None:
        self._requests: _RequestsModuleProtocol = _REQUESTS
        self._http_adapter_cls: type[HTTPAdapter] = _HTTP_ADAPTER_CLS
        self._retry_cls: type[Retry] = _RETRY_CLS
        self._config = config or HTTPSessionConfig()
        self._lock = threading.Lock()
        self._sessions: dict[str, _RequestsSessionProtocol] = {}

    def session_for(self, endpoint: str) -> _RequestsSessionProtocol:
        """Return a pooled session for the provided endpoint."""

        normalized = (endpoint or "").strip()
        key = normalized.lower() if normalized else "__default__"
        with self._lock:
            existing = self._sessions.get(key)
            if existing is not None:
                return existing
            session = self._build_session()
            self._sessions[key] = session
            return session

    def reset_session(self, endpoint: str) -> None:
        """Dispose of any cached session for the endpoint."""

        normalized = (endpoint or "").strip()
        key = normalized.lower() if normalized else "__default__"
        session: _RequestsSessionProtocol | None
        with self._lock:
            session = self._sessions.pop(key, None)
        if session is None:
            return
        try:
            session.close()
        except Exception:  # pragma: no cover - best-effort cleanup
            pass

    def _build_session(self) -> _RequestsSessionProtocol:
        """Create a new configured ``requests.Session`` instance."""

        retry_cfg = self._config.retry
        allowed_methods = frozenset(method.upper() for method in retry_cfg.allowed_methods)
        retry = self._retry_cls(
            total=retry_cfg.total,
            connect=retry_cfg.total,
            read=retry_cfg.total,
            status=retry_cfg.total,
            backoff_factor=retry_cfg.backoff_factor,
            status_forcelist=retry_cfg.status_forcelist,
            allowed_methods=allowed_methods,
            respect_retry_after_header=retry_cfg.respect_retry_after_header,
            raise_on_status=False,
        )
        adapter = self._http_adapter_cls(
            max_retries=retry,
            pool_connections=self._config.pool_maxsize,
            pool_maxsize=self._config.pool_maxsize,
        )
        session = self._requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session


__all__ = [
    "HTTPRetryConfig",
    "HTTPSessionConfig",
    "RequestsSessionManager",
    "RequestsSessionProtocol",
]
RequestsSessionProtocol = _RequestsSessionProtocol
