from __future__ import annotations

from .base import Court

# Minimal, opinionated mapping for common filings → required division
FILING_DIVISION_HINTS: dict[str, str] = {
    "STATEMENT_OF_CLAIM": "CIVIL",
    "STATEMENT_OF_DEFENCE": "CIVIL",
    "ORIGINATING_APPLICATION": "CIVIL",
    "COUNTERCLAIM": "CIVIL",
    "AFFIDAVIT": "CIVIL",
    "FAMILY_APPLICATION": "FAMILY",
    "NOTICE_OF_APPEAL": "APPEALS",
    "APPEAL_RECORD": "APPEALS",
}

# For each division, at least one hearing category should exist
DIVISION_HEARING_REQUIRED_PREFIXES: dict[str, tuple[str, ...]] = {
    "CIVIL": ("CIV_MOTIONS_", "CIV_CASE_MGMT_CONF", "CIV_PRE_TRIAL_CONF", "CIV_TRIAL_"),
    "FAMILY": ("FAM_",),
    "CRIMINAL": ("CRIM_",),
    "TRAFFIC": ("TRAFFIC_",),
    "APPEALS": ("APP_",),
    "APPLICATIONS": (
        "CIV_MOTIONS_",
        "FAM_",
        "APP_",
    ),  # flexible, but must map to one of these lists
    "COMMERCIAL": ("CIV_MOTIONS_", "CIV_TRIAL_"),
    "PROBATE": ("CIV_",),
    "YOUTH": ("CRIM_", "FAM_"),
}


def check_filing_division_consistency(court: Court) -> list[str]:
    issues: list[str] = []
    for fc in court.filing_codes or []:
        # expect fc.category and fc.code.code exist; parse division from LocalCode
        code = fc.code.code if getattr(fc, "code", None) else ""
        parts = code.split(".")
        div = parts[4] if len(parts) > 4 else ""
        required = FILING_DIVISION_HINTS.get(fc.category, None)
        if required and div != required:
            issues.append(
                (
                    f"{court.key}: filing {fc.category} is in division {div}, expected "
                    f"{required} ({code})"
                )
            )
    return issues


def check_hearing_order_crossmap(court: Court) -> list[str]:
    issues: list[str] = []
    hearing_divs: dict[str, bool] = {}

    # collect divisions present in hearing codes via LocalCode
    for hc in court.hearing_codes or []:
        parts = hc.code.code.split(".")
        if len(parts) > 4:
            hearing_divs[parts[4]] = True

    # for each ORDER, ensure court has at least one hearing in the same division
    for oc in court.order_codes or []:
        code = oc.code.code
        parts = code.split(".")
        div = parts[4] if len(parts) > 4 else ""
        if not div:
            issues.append(f"{court.key}: order with no division segment {code}")
            continue

        # soft requirement: check division mapping coverage
        if div not in hearing_divs:
            # fallback: ensure division maps to at least one of the expected hearing prefixes
            req_prefixes = DIVISION_HEARING_REQUIRED_PREFIXES.get(div, tuple())
            if not req_prefixes:
                continue
            # If no hearing code matches any prefix -> flag
            found = False
            for hc in court.hearing_codes or []:
                if any(hc.category.startswith(p) for p in req_prefixes):
                    found = True
                    break
            if not found:
                issues.append(
                    f"{court.key}: no hearing categories found for order division {div} ({code})"
                )
    return issues
