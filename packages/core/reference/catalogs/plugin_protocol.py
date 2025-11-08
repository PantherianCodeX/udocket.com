from __future__ import annotations

from collections.abc import Iterable

from ..taxonomy.categories import CountryCode
from .base import CourtCatalog

EXPORT_FN_NAME = "export_catalogs"  # kept for compatibility (if you ever export from code)


def validate_catalogs(catalogs: Iterable[CourtCatalog]) -> None:
    for c in catalogs:
        assert isinstance(c.country, CountryCode)
        assert c.courts, "CourtCatalog must contain at least one Court."
        for key, court in c.courts.items():
            assert court.locations, f"Court {key} missing locations."
            for lt in court.hearing_codes + court.filing_codes + court.order_codes:
                _ = lt.code.namespace()  # raises if invalid
