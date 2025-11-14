from __future__ import annotations

import re
from collections.abc import Sequence
from re import Pattern

from .base import (
    CaseNumber,
    CaseNumberScheme,
    ConstraintDecl,
    DerivationDecl,
    RegexRule,
    Transform,
)
from .registry import all_schemes, schemes_by_court


class CaseNumberEngine:
    """
    Small helper to work with a fixed set of schemes (useful in services).
    """

    def __init__(self, schemes: list[CaseNumberScheme] | None = None) -> None:
        self._schemes = schemes or list(all_schemes())

    def match(self, value: str, court_key_hint: str | None = None) -> CaseNumber | None:
        if court_key_hint:
            for s in schemes_by_court().get(court_key_hint, []):
                try:
                    res = _try_scheme(value, s)
                    if res:
                        return res
                except Exception:
                    continue
            return None

        for s in self._schemes:
            try:
                res = _try_scheme(value, s)
                if res:
                    return res
            except Exception:
                continue
        return None

    def validate(self, value: str, court_key_hint: str | None = None) -> CaseNumber:
        if court_key_hint:
            for s in schemes_by_court().get(court_key_hint, []):
                res = _try_scheme(value, s)
                if res:
                    return res
            raise ValueError("No scheme matched for hinted court")
        # fall back to global validator for detailed errors
        return validate_case_number(value)


def _compile_flags(flags: Sequence[str]) -> int:
    f = 0
    for fl in flags:
        if fl == "IGNORECASE":
            f |= re.IGNORECASE
        elif fl == "MULTILINE":
            f |= re.MULTILINE
    return f


def _apply_transform(s: str, t: Transform) -> str:
    if t.op == "UPPER":
        return s.upper()
    if t.op == "LOWER":
        return s.lower()
    if t.op == "TRIM":
        return s.strip()
    if t.op == "REMOVE_CHARS":
        chars = t.arg or ""
        return s.translate({ord(c): None for c in chars})
    if t.op == "KEEP_ALNUM":
        return "".join(ch for ch in s if ch.isalnum())
    if t.op == "REGEX_SUB":
        args = t.arg if isinstance(t.arg, dict) else {}
        pat_s = str(args.get("pattern", ""))
        if not pat_s:
            return s
        repl = str(args.get("repl", ""))
        pat = re.compile(pat_s, re.IGNORECASE)
        return pat.sub(repl, s)
    return s


def _normalize(value: str, rule: RegexRule) -> tuple[str, Pattern[str]]:
    s = value
    for tr in rule.transforms or []:
        s = _apply_transform(s, tr)
    pat: Pattern[str] = re.compile(rule.pattern, _compile_flags(rule.flags))
    return s, pat


def _enforce_constraints(
    court_key: str, parts: dict[str, str], constraints: list[ConstraintDecl]
) -> None:
    for c in constraints or []:
        v = parts.get(c.group, "")
        if c.kind == "year_range":
            if not v.isdigit():
                raise ValueError(f"group '{c.group}' not numeric")
            iv = int(v)
            if (c.min is not None and iv < c.min) or (c.max is not None and iv > c.max):
                raise ValueError(f"group '{c.group}' out of range [{c.min},{c.max}]")
        elif c.kind == "length":
            ln = len(v)
            if (c.min is not None and ln < c.min) or (c.max is not None and ln > c.max):
                raise ValueError(f"group '{c.group}' length not in [{c.min},{c.max}]")
        elif c.kind == "enum":
            if c.allowed is not None and v not in c.allowed:
                raise ValueError(f"group '{c.group}' not in allowed set")
        elif c.kind == "in_catalog_location_codes":
            # Stubbed for POC: do not enforce until official codes are provided.
            # Other constraints (regex/length/year_range) still apply.
            pass


def _year_2_to_4(two: str, floor: int = 1980) -> str:
    if not two.isdigit():
        return two
    yy = int(two)
    century = (floor // 100) * 100
    year = century + yy
    if year < floor:
        year += 100
    return f"{year:04d}"


def _apply_derivations(parts: dict[str, str], derivs: list[DerivationDecl]) -> dict[str, str]:
    out = dict(parts)
    for d in derivs or []:
        if d.kind == "YEAR_2_TO_4":
            src = d.src
            dest = d.dest
            out[dest] = _year_2_to_4(parts.get(src, ""), d.century_floor or 1980)
        elif d.kind == "MAP":
            src = parts.get(d.src, "")
            out[d.dest] = (d.mapping or {}).get(src, src)
        elif d.kind == "JOIN":
            seq = [parts.get(s, "") for s in (d.src or [])]
            out[d.dest] = (d.sep or "").join(seq)
    return out


def _try_scheme(value: str, scheme: CaseNumberScheme) -> CaseNumber | None:
    for r in scheme.rules:
        normalized, pat = _normalize(value, r)
        m = pat.match(normalized)
        if not m:
            continue
        parts = {k: (v or "") for k, v in m.groupdict().items()}
        _enforce_constraints(scheme.court_key, parts, scheme.constraints)
        derived = _apply_derivations(parts, scheme.derivations)
        normalized_out = derived.get("normalized", normalized)
        return CaseNumber(
            value=value,
            court_key=scheme.court_key,
            scheme_key=scheme.key,
            normalized=normalized_out,
            parts=derived,
        )
    return None


def validate_case_number(value: str, court_key_hint: str | None = None) -> CaseNumber:
    """
    Validate a value against schemes. If court_key_hint provided, only that court is tried.
    Otherwise, auto-detects across all known schemes.
    """
    errors: list[str] = []
    if court_key_hint:
        for s in schemes_by_court().get(court_key_hint, []):
            try:
                result = _try_scheme(value, s)
                if result:
                    return result
            except Exception as e:
                errors.append(f"{s.key}: {e}")
        raise ValueError("; ".join(errors) or "No match")

    # autodetect across all schemes
    for s in all_schemes():
        try:
            result = _try_scheme(value, s)
            if result:
                return result
        except Exception as e:
            errors.append(f"{s.key}: {e}")

    raise ValueError("; ".join(errors) or "No scheme matched")


# --- Convenience wrappers -----------------------------------------------------


def load_case_number_schemes() -> list[CaseNumberScheme]:
    """Return all registered schemes (wrapper around registry)."""
    return list(all_schemes())


def match_case_number(value: str, court_key_hint: str | None = None) -> CaseNumber | None:
    """Like validate_case_number but returns None instead of raising."""
    try:
        return validate_case_number(value, court_key_hint=court_key_hint)
    except Exception:
        return None
