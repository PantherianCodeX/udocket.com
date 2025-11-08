from collections.abc import Mapping

class Response:
    status_code: int

    def raise_for_status(self) -> None: ...

    def json(self) -> Mapping[str, object]: ...

def post(
    url: str,
    *,
    headers: Mapping[str, str] | None,
    data: str | bytes,
    timeout: int,
) -> Response: ...
