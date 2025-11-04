# pyright: strict

"""Core helpers shared across uDocket services."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("udocket_core")
except PackageNotFoundError:  # local dev / editable installs
    __version__ = "0.0.0"

# Re-export common entry points
from .reference.catalogs.base import CatalogBundle
from .reference.catalogs.registry import discover_catalogs
from .reference.identifiers.base import CaseNumber
from .reference.identifiers.engine import (
    CaseNumberEngine,
    load_case_number_schemes,
    match_case_number,
    validate_case_number,
)
from .reference.identifiers.registry import all_schemes, schemes_by_court

__all__ = [
    "__doc__",
    "__version__",
    "discover_catalogs",
    "CatalogBundle",
    "CaseNumberEngine",
    "load_case_number_schemes",
    "match_case_number",
    "validate_case_number",
    "CaseNumber",
    "schemes_by_court",
    "all_schemes",
]
