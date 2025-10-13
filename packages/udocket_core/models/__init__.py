from .version import __version__
# Keep the models surface small, stable, and accurate.
from .reference.registry import discover_catalogs

from .reference.base import (
    CatalogBundle,
    CourtCatalog,
    Court,
    CourtLevel,
    Location,
    FilingCode,
    HearingCode,
    OrderCode,
)

# Taxonomy (public, top-level)
from .taxonomy.categories import (
    CountryCode,
    CourtLevel,
    Division,
    HearingCategory,
    FilingCategory,
    OrderCategory,
)
from .taxonomy.namespace import LocalCode

# Identifiers
from .identifiers.base import (
    CaseNumber,
    CaseNumberScheme,
    RegexRule,
    Transform,
    ConstraintDecl,
    DerivationDecl,
)

from .identifiers.registry import schemes_by_court, all_schemes
from .identifiers.engine import (
    CaseNumberEngine,
    load_case_number_schemes,
    match_case_number,
    validate_case_number,
)

__all__ = [
    # reference models
    "CatalogBundle",
    "CourtCatalog",
    "Court",
    "Location",
    "FilingCode",
    "HearingCode",
    "OrderCode",
    "discover_catalogs",
    # taxonomy
    "CountryCode",
    "CourtLevel",
    "Division",
    "HearingCategory",
    "FilingCategory",
    "OrderCategory",
    "LocalCode",
    # identifiers
    "CaseNumber",
    "CaseNumberScheme",
    "RegexRule",
    "Transform",
    "ConstraintDecl",
    "DerivationDecl",
    "schemes_by_court",
    "all_schemes",
    "CaseNumberEngine",
    "load_case_number_schemes",
    "match_case_number",
    "validate_case_number",
]

