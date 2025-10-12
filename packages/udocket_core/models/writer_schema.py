# filename: udocket_models/writer_schema.py
from __future__ import annotations
from .core import UBase
from .proceedings import Jurisdiction, CaseHeader, ProceduralRecord
from .parties import Actors
from .factual import FactualRecord
from .issues import IssuesFrame
from .evidence import EvidenceBundle
from .deadlines import Deadlines
from .comms import Communications
from .outputs import Outputs
from .safety import Safety
from .meta import Meta

class CaseSummary(UBase):
    """LLM-native case summarization model (AB-focused but globally compatible)."""
    jurisdiction: Jurisdiction
    case_header: CaseHeader
    actors: Actors
    procedural: ProceduralRecord
    factual: FactualRecord
    issues: IssuesFrame
    evidence: EvidenceBundle
    deadlines: Deadlines
    communications: Communications
    outputs: Outputs
    safety: Safety
    meta: Meta
