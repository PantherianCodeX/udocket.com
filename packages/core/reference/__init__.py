from .catalogs.base import (
    CatalogBundle,
    Court,
    CourtCatalog,
    FilingCode,
    HearingCode,
    Location,
    OrderCode,
)

# Keep the models surface small, stable, and accurate.
from .catalogs.registry import discover_catalogs

# Identifiers
from .identifiers.base import (
    CaseNumber,
    CaseNumberScheme,
    ConstraintDecl,
    DerivationDecl,
    RegexRule,
    Transform,
)
from .identifiers.engine import (
    CaseNumberEngine,
    load_case_number_schemes,
    match_case_number,
    validate_case_number,
)
from .identifiers.registry import all_schemes, schemes_by_court

# Taxonomy (public, top-level)
from .taxonomy.categories import (
    CountryCode,
    CourtLevel,
    Division,
    FilingCategory,
    HearingCategory,
    OrderCategory,
)
from .taxonomy.namespace import LocalCode
from .version import __version__

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
    "__version__",
]
