from __future__ import annotations

from typing import Any, Optional

class Case:
    id: str
    organization_id: str
    reviewer_id: Optional[int]
    memberships: Any  # reverse FK manager

class CaseMembership:
    case_id: str
    user_id: int

__all__ = ["Case", "CaseMembership"]

