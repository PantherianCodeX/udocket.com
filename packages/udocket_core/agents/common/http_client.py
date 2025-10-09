from __future__ import annotations

# pyright: strict

import threading
from dataclasses import dataclass
from typing import Mapping, Protocol


class _RequestsResponseProtocol(Protocol):
    status_code: int
    text: str
    headers: Mapping[str, object] | None

    def json(self) -> object: ...


class _RequestsSessionProtocol(Protocol):
    def post(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        json: object | None = None,
        timeout: int | float | None = None,
    ) -> _RequestsResponseProtocol: ...

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: int | float | None = None,
    ) -> _RequestsResponseProtocol: ...


class _RequestsModuleProtocol(Protocol):
    class exceptions(Protocol):  # type: ignore[misc]
        HTTPError: type[Exception]
        RequestException: type[Exception]

    Session: type[_RequestsSessionProtocol]


try:  # pragma: no cover - optional dependency guard
    import requests as _imported_requests
    from requests.adapters import HTTPAdapter as _HTTPAdapter
except Exception:  # pragma: no cover - requests absent
    _imported_requests = None
    _HTTPAdapter = None

try:  # pragma: no cover - optional dependency guard
    from urllib3.util.retry import Retry as _Retry
except Exception:  # pragma: no cover - urllib3 absent
    _Retry = None


def _require_requests_dependencies() -> tuple[_RequestsModuleProtocol, type, type]:
    if _imported_requests is None or _HTTPAdapter is None or _Retry is None:  # pragma: no cover - defensive
        raise RuntimeError("requests and urllib3 are required for HTTP session management")
    return (
        _imported_requests,  # type: ignore[return-value]
        _HTTPAdapter,  # type: ignore[return-value]
        _Retry,  # type: ignore[return-value]
    )


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
        requests_module, http_adapter_cls, retry_cls = _require_requests_dependencies()
        self._requests: _RequestsModuleProtocol = requests_module
        self._http_adapter_cls = http_adapter_cls
        self._retry_cls = retry_cls
        self._config = config or HTTPSessionConfig()
        self._lock = threading.Lock()
        self._sessions: dict[str, _RequestsSessionProtocol] = {}

    def session_for(self, endpoint: str) -> _RequestsSessionProtocol:
        normalized = (endpoint or "").strip()
        key = normalized.lower() if normalized else "__default__"
        with self._lock:
            existing = self._sessions.get(key)
            if existing is not None:
                return existing
            session = self._build_session()
            self._sessions[key] = session
            return session

    def _build_session(self) -> _RequestsSessionProtocol:
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
