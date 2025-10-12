from __future__ import annotations
import os
from packages.udocket_core.models.reference.registry import discover_catalogs

def test_all_catalogs_load_and_validate():
    # Allow overriding data dir in CI; otherwise default package data is used
    data_root = os.getenv("COURT_CATALOG_ROOT", None)
    catalogs = discover_catalogs(data_root)
    assert len(catalogs) > 0

def test_ab_acj_locations_present_if_available():
    # This is a sanity check that our reference data is intact.
    data_root = os.getenv("COURT_CATALOG_ROOT", None)
    catalogs = discover_catalogs(data_root)
    ab = next((c for c in catalogs if c.country.value == "CA" and c.subnational == "AB"), None)
    if not ab:
        # If the AB bundle isn't present in a given deployment, skip gracefully.
        return
    acj = ab.courts.get("CA-AB-ACJ")
    assert acj is not None
    # We documented 72 ACJ locations. If that ever changes, update the data and this test together.
    assert len(acj.locations) == 72
    # Ensure at least one base point exists (validator enforces, but keep a fast check here)
    assert any(l.is_base_point for l in acj.locations)
