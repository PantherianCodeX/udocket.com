# pyright: strict

"""Core helpers shared across uDocket services."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("udocket_core")
except PackageNotFoundError:  # local dev / editable installs
    __version__ = "0.0.0"

# Re-export common entry points
from .models.reference.registry import discover_catalogs
from .models.reference.base import CatalogBundle
from .models.identifiers.engine import (
    CaseNumberEngine,
    load_case_number_schemes,
    match_case_number,
    validate_case_number,
)
from .models.identifiers.base import CaseNumber
from .models.identifiers.registry import schemes_by_court, all_schemes

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
