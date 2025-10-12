# pyright: reportUnsupportedDunderAll=false
"""
udocket_core.models
-------------------
Module initialization and public exports.
Dynamically includes all *Enum classes in __all__ for convenience.
"""

# Base models
from .core import UBase, IdStr, Money, Provenance

# Enums (import them so they're visible to dir())
from .enums import *

# Other model groups
from .parties import Party, Representative, Actors
from .proceedings import CaseHeader, ProceduralRecord, Filing, Order, Hearing
from .factual import FactualRecord, FactUnit
from .issues import IssuesFrame, Issue
from .evidence import EvidenceBundle, EvidenceItem
from .deadlines import Deadlines, DeadlineEntry, RuleBasis
from .comms import Communications, Interview, InterviewSegment
from .outputs import Outputs, RenderPlan, RenderSection
from .safety import Safety
from .meta import Meta
from .writer_schema import CaseSummary  # AB-LLM writer schema (v2) pydantic translation

from .registry import JurisdictionKey, CourtRegistry
# Jurisdiction registries
from .reference.ca_ab import AlbertaCourtCatalog
from .reference.ca_federal import CanadaFederalCatalog
from .reference.us_ny import NewYorkCourtCatalog


# Base exports
__all__ = [
    # base
    "UBase", "IdStr", "Money", "Provenance",
    # models
    "Party", "Representative", "Actors",
    "CaseHeader", "ProceduralRecord", "Filing", "Order", "Hearing",
    "FactualRecord", "FactUnit",
    "IssuesFrame", "Issue",
    "EvidenceBundle", "EvidenceItem",
    "Deadlines", "DeadlineEntry", "RuleBasis",
    "Communications", "Interview", "InterviewSegment",
    "Outputs", "RenderPlan", "RenderSection",
    "Safety", "Meta",
    "CaseSummary",
    # registries
    "JurisdictionKey", "CourtRegistry",
    "AlbertaCourtCatalog", "CanadaFederalCatalog", "NewYorkCourtCatalog",
]

# Dynamically include all Enums (so you don't have to list them manually)
# Note: This assumes all your Enum classes are defined in the imported modules
# and follow the naming convention of ending with "Enum".
__all__.extend(n for n in dir() if n.endswith("Enum"))
