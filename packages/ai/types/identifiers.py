"""Strongly typed identifier aliases used across the AI runtime."""

from __future__ import annotations

# pyright: strict
from typing import NewType

OrganizationID = NewType("OrganizationID", str)
CaseID = NewType("CaseID", str)
JobID = NewType("JobID", str)
ArtifactID = NewType("ArtifactID", str)
ProviderName = NewType("ProviderName", str)
ModelName = NewType("ModelName", str)
RouteName = NewType("RouteName", str)
CapabilityName = NewType("CapabilityName", str)

__all__ = [
    "ArtifactID",
    "CapabilityName",
    "CaseID",
    "JobID",
    "ModelName",
    "OrganizationID",
    "ProviderName",
    "RouteName",
]
