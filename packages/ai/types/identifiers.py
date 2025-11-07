from __future__ import annotations

# pyright: strict

"""Strongly typed identifier aliases used across the AI runtime."""

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
    "CaseID",
    "CapabilityName",
    "JobID",
    "ModelName",
    "OrganizationID",
    "ProviderName",
    "RouteName",
]
