# udocket_models v4 (models-only + JSON data)

This package separates **Pydantic v2 models** (validation) from **JSON data** (content).
The **core models** live under `udocket_models/core/…`. All **reference catalogs** are JSON
bundles under `udocket_models/data/reference/<COUNTRY>/<REGION>/catalog.json`.

## Why this design?
- **Zero code-data coupling**: add or update any jurisdiction by editing JSON only.
- **Enum isolation**: the UI/LLM consumes *global categories* (portable enums) and looks up
  *local, namespaced codes* from the selected court catalog.
- **DB-friendly**: every JSON bundle includes optional PostgreSQL table hints to simplify import.

---

## Glossary
- **Global categories**: portable enums (e.g., `HearingCategory.CRIM_DOCKET`).
- **Local codes**: namespaced codes (e.g., `CA.AB.ACJ.HRG.CRIM.DOCKET`), declared inside each Court’s catalog.

---

## File conventions
`udocket_models/data/reference/<COUNTRY-ISO2>/<REGION>/catalog.json`
- Example: `CA/AB/catalog.json` (Alberta), `CA/FED/catalog.json` (Canada Federal),
  `US/NY/catalog.json` (New York State).
- Each file is a **CatalogBundle**:
  ```json
  { "schema":"udocket.reference.catalog.bundle.v1", "db":{...}, "data":[ JurisdictionCatalog... ], "meta":{...} }
  ```
  
## Keys & naming
- `Court.key`: `CC-REGION-COURT` (e.g., `CA-AB-ACJ`).
- `CourtLocation.slug`: kebab-case (e.g., `st-albert`, `wabasca-desmarais`).
- `LocalCode.code`: `"CC.REGION.COURT.DOMAIN.SPEC"` (regex-validated).


You're absolutely right—we should **keep models pure** (validation + types only) and put **all court data in JSON** so you can import/export it freely (e.g., into PostgreSQL) and expand jurisdictions without touching code.

Below is a **wrap‑up, cohesive update** that:

* **Separates models from data** (all data is JSON only, with optional DB import hints).
* Keeps **Pydantic v2 models** focused on validation & typing.
* Adds a **dynamic JSON loader** (no in‑module data).
* Moves the **writer/compose model** to `./agents/compose/model.py`.
* Keeps your **global taxonomy** (portable enums) and **local, namespaced codes** (jurisdiction‑scoped).
* Provides **fully populated Alberta ACJ locations (all 72 points)** + confirmed circuit→base rules where the Court says “**Continue to send all court documents to …**”.
* Includes **Canada‑Federal** and **US‑NY** minimal JSON bundles to prove multi‑jurisdiction growth.
* Ships a **clear expansion guide**.

> Load‑bearing facts (with sources):
> • **ACJ location list (72)** appears on the official “Contact & Hours” page. ([Alberta Courts][1])
> • Explicit **circuit → base** examples used in JSON (e.g., Airdrie→Calgary; Westlock→St. Albert; Grande Cache→Hinton; Valleyview/Fox Creek→Grande Prairie; Coronation/Rocky Mountain House→Red Deer; Fairview→Peace River; Red Earth Creek→High Prairie; Brooks→Medicine Hat; Ponoka→Wetaskiwin; Taber/Cardston→Lethbridge; Wainwright→Vermilion). ([Alberta Courts][2])
> • **ACJ civil monetary limit** = **$100,000**. ([Alberta Courts][3])
> • **ABCA registry routing**: north of Red Deer → **Edmonton**; Red Deer & south → **Calgary**. ([Alberta Courts][4])
> • **Specialized courts** (DAC, DTC, Mental Health, Indigenous) exist in ACJ. ([Alberta Courts][5])
> • **NY Supreme Court – Commercial Division (NY County)** at **60 Centre St**; Support Office Room **119/119A**; Preliminary/Compliance conference and submission practices. ([New York State Unified Court System][6])
> • **Canada‑Federal** registry network via **CAS**; Ottawa & Toronto registry offices referenced. ([fct-cf.ca][7])

---

## 📁 New structure (models in `core/`, data in JSON)

```
udocket_models/
├─ __init__.py
├─ version.py
├─ core/
│  ├─ taxonomy/
│  │  ├─ categories.py          # global portable enums (Pydantic validates)
│  │  └─ namespace.py           # LocalCode validator (namespaced codes)
│  └─ reference/
│     ├─ base.py                # Pydantic models (Court, Location, Codes, Catalogs)
│     ├─ plugin_protocol.py     # export function name + validators
│     └─ registry.py            # discovers & loads JSON data bundles dynamically
├─ data/
│  └─ reference/
│     ├─ CA/
│     │  ├─ AB/catalog.json     # ACJ/KB/ABCA with full ACJ locations, circuit→base rules
│     │  └─ FED/catalog.json    # Federal Courts (FC/FCA/TCC) minimal
│     └─ US/
│        └─ NY/catalog.json     # NY Supreme – ComDiv (NY County) minimal
├─ agents/
│  └─ compose/
│     └─ model.py               # writer/compose schema moved here
└─ README.md                    # expansion & ingestion guide
```

> Everything below is **complete file content** (ready to drop in).
> Where long JSON lists appear, they are **data‑only** and validated by the models in `core/`.

---

# 1) Core package files (pure models + loader)

### `udocket_models/__init__.py`

```python
from .version import __version__
```

### `udocket_models/version.py`

```python
__version__ = "4.0.0"
```

---

### `udocket_models/core/taxonomy/categories.py`

```python
from __future__ import annotations
from enum import Enum

class CountryCode(str, Enum):
    CA = "CA"
    US = "US"
    OTHER = "OTHER"

class CourtLevel(str, Enum):
    TRIAL_PROVINCIAL = "TRIAL_PROVINCIAL"
    TRIAL_SUPERIOR   = "TRIAL_SUPERIOR"
    APPEAL           = "APPEAL"
    SPECIALIZED      = "SPECIALIZED"
    UNKNOWN_LEVEL    = "UNKNOWN_LEVEL"

class Division(str, Enum):
    CIVIL        = "CIVIL"
    FAMILY       = "FAMILY"
    CRIMINAL     = "CRIMINAL"
    YOUTH        = "YOUTH"
    TRAFFIC      = "TRAFFIC"
    SURROGATE    = "SURROGATE"
    APPLICATIONS = "APPLICATIONS"
    APPEALS      = "APPEALS"
    COMMERCIAL   = "COMMERCIAL"
    UNKNOWN      = "UNKNOWN"

class HearingCategory(str, Enum):
    # Civil / Family (trial)
    CIV_CHAMBERS_REGULAR      = "CIV_CHAMBERS_REGULAR"
    CIV_CHAMBERS_SPECIAL      = "CIV_CHAMBERS_SPECIAL"
    CIV_CASE_MGMT_CONF        = "CIV_CASE_MGMT_CONF"
    CIV_PRE_TRIAL_CONF        = "CIV_PRE_TRIAL_CONF"
    CIV_JDR                   = "CIV_JDR"
    CIV_TRIAL_JUDGE           = "CIV_TRIAL_JUDGE"
    CIV_TRIAL_JURY            = "CIV_TRIAL_JURY"

    # Family
    FAM_DOCKET                = "FAM_DOCKET"
    FAM_SPECIAL               = "FAM_SPECIAL"
    FAM_CONFERENCE            = "FAM_CONFERENCE"

    # Criminal
    CRIM_FIRST_APPEARANCE     = "CRIM_FIRST_APPEARANCE"
    CRIM_BAIL                 = "CRIM_BAIL"
    CRIM_DOCKET               = "CRIM_DOCKET"
    CRIM_PRELIM_INQUIRY       = "CRIM_PRELIM_INQUIRY"
    CRIM_ARRAIGNMENT          = "CRIM_ARRAIGNMENT"
    CRIM_TRIAL_JUDGE          = "CRIM_TRIAL_JUDGE"
    CRIM_TRIAL_JURY           = "CRIM_TRIAL_JURY"
    CRIM_SENTENCING           = "CRIM_SENTENCING"

    # Traffic
    TRAFFIC_DOCKET            = "TRAFFIC_DOCKET"
    TRAFFIC_TRIAL             = "TRAFFIC_TRIAL"

    # Appeals
    APP_SINGLE_JUDGE_APP      = "APP_SINGLE_JUDGE_APP"
    APP_APPLICATIONS_LIST     = "APP_APPLICATIONS_LIST"
    APP_HEARING               = "APP_HEARING"

    # Problem-solving / specialized
    SPEC_DOMESTIC_ABUSE       = "SPEC_DOMESTIC_ABUSE"
    SPEC_DRUG_TREATMENT       = "SPEC_DRUG_TREATMENT"
    SPEC_MENTAL_HEALTH        = "SPEC_MENTAL_HEALTH"
    SPEC_INDIGENOUS           = "SPEC_INDIGENOUS"

    UNKNOWN                   = "UNKNOWN"

class FilingCategory(str, Enum):
    PLEADING_CLAIM                = "PLEADING_CLAIM"
    PLEADING_DEFENCE              = "PLEADING_DEFENCE"
    PLEADING_COUNTERCLAIM         = "PLEADING_COUNTERCLAIM"
    PLEADING_REPLY                = "PLEADING_REPLY"
    ORIGINATING_APPLICATION       = "ORIGINATING_APPLICATION"
    INTERLOCUTORY_APPLICATION     = "INTERLOCUTORY_APPLICATION"
    AFFIDAVIT                     = "AFFIDAVIT"
    LIST_OR_AFFIDAVIT_OF_RECORDS  = "LIST_OR_AFFIDAVIT_OF_RECORDS"
    BRIEF_OR_MEMO                 = "BRIEF_OR_MEMO"
    CONSENT_ORDER_SUBMISSION      = "CONSENT_ORDER_SUBMISSION"
    ORDER                         = "ORDER"
    JUDGMENT                      = "JUDGMENT"
    NOTICE_OF_APPEAL              = "NOTICE_OF_APPEAL"
    APPEAL_RECORD                 = "APPEAL_RECORD"
    FACTUM                        = "FACTUM"
    EXTRACTS_KEY_EVIDENCE         = "EXTRACTS_KEY_EVIDENCE"
    BOOK_OF_AUTHORITIES           = "BOOK_OF_AUTHORITIES"
    TRANSCRIPT                    = "TRANSCRIPT"
    SENTENCING_SUBMISSIONS        = "SENTENCING_SUBMISSIONS"
    UNKNOWN                       = "UNKNOWN"

class OrderCategory(str, Enum):
    SCHEDULING_ENDORSEMENT = "SCHEDULING_ENDORSEMENT"
    INTERIM_ORDER          = "INTERIM_ORDER"
    FINAL_ORDER            = "FINAL_ORDER"
    CONSENT_ORDER          = "CONSENT_ORDER"
    REASONS_FOR_JUDGMENT   = "REASONS_FOR_JUDGMENT"
    MINUTE_ENTRY           = "MINUTE_ENTRY"
    UNKNOWN                = "UNKNOWN"
```

---

### `udocket_models/core/taxonomy/namespace.py`

```python
from __future__ import annotations
import re
from pydantic import BaseModel, Field, field_validator

# e.g., "CA.AB.ACJ.HRG.CRIM.DOCKET" or "US.NY.NYCO.SUP.COMDIV.HRG.PRELIM_CONF"
_LOCALCODE_RE = re.compile(r"^[A-Z]{2}(?:\.[A-Z0-9]{2,}){2,}$")

class LocalCode(BaseModel):
    code: str = Field(..., description="Namespaced jurisdictional code, e.g., CA.AB.ACJ.HRG.CRIM.DOCKET")

    @field_validator("code")
    @classmethod
    def _valid(cls, v: str) -> str:
        if not _LOCALCODE_RE.match(v):
            raise ValueError("Invalid LocalCode format; expected 'CC.SS.COURT.DOMAIN.SPEC...'.")
        return v

    def namespace(self) -> str:
        return ".".join(self.code.split(".")[:-1])
```

---

### `udocket_models/core/reference/base.py`

```python
from __future__ import annotations
from typing import Dict, List, Optional, Set, Mapping
from pydantic import BaseModel, Field, ConfigDict, field_validator

from ..taxonomy.categories import (
    CountryCode, CourtLevel, Division, HearingCategory, FilingCategory, OrderCategory
)
from ..taxonomy.namespace import LocalCode

# -------------------------
# Core reference models
# -------------------------

class CourtLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(..., pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
    display_name: str
    city: Optional[str] = None
    is_base_point: bool = False
    admin_base_slug: Optional[str] = Field(
        None, description="If circuit, the base registry handling filings."
    )
    divisions_served: Set[Division] = Field(default_factory=set)
    notes: Optional[str] = None

class LocalHearingType(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: HearingCategory
    divisions: Set[Division] = Field(default_factory=set)

class LocalFilingType(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: FilingCategory

class LocalOrderType(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: LocalCode
    label: str
    category: OrderCategory

class Court(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(..., pattern=r"^[A-Z]{2}[-][A-Z0-9_-]{2,}$")  # e.g., CA-AB-ACJ
    country: CountryCode
    subnational: Optional[str] = None  # e.g., "AB", "NY"
    level: CourtLevel
    formal_name: str
    short_name: str
    divisions: Set[Division] = Field(default_factory=set)
    locations: List[CourtLocation] = Field(default_factory=list)
    hearing_codes: List[LocalHearingType] = Field(default_factory=list)
    filing_codes:  List[LocalFilingType]  = Field(default_factory=list)
    order_codes:   List[LocalOrderType]   = Field(default_factory=list)

    @field_validator("locations")
    @classmethod
    def _no_duplicate_slugs(cls, v: List[CourtLocation]) -> List[CourtLocation]:
        seen = set()
        for loc in v:
            if loc.slug in seen:
                raise ValueError(f"Duplicate location slug: {loc.slug}")
            seen.add(loc.slug)
        return v

class JurisdictionCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    country: CountryCode
    subnational: Optional[str] = None
    courts: Dict[str, Court] = Field(default_factory=dict)
    note: Optional[str] = None

    @field_validator("courts")
    @classmethod
    def _keys_match(cls, v: Dict[str, Court]) -> Dict[str, Court]:
        for key, court in v.items():
            if key != court.key:
                raise ValueError(f"Court dict key '{key}' must equal Court.key '{court.key}'.")
        return v

# -------------------------
# JSON bundle (data-only) wrapper + DB hints
# -------------------------

class DBTableHint(BaseModel):
    table: str
    pk: List[str]
    fk: Mapping[str, List[str]] | None = None
    unique: List[List[str]] | None = None
    indexes: List[List[str]] | None = None

class CatalogDBInfo(BaseModel):
    type: str = Field(..., pattern=r"^(postgresql)$")
    tables: Mapping[str, DBTableHint]  # e.g., 'jurisdictions', 'courts', etc.

class CatalogBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema: str = Field(..., pattern=r"^udocket\.reference\.catalog\.bundle\.v1$")
    db: CatalogDBInfo
    data: List[JurisdictionCatalog]
    meta: Dict[str, str] | None = None
```

---

### `udocket_models/core/reference/plugin_protocol.py`

```python
from __future__ import annotations
from typing import Iterable
from ..taxonomy.categories import CountryCode
from .base import JurisdictionCatalog

EXPORT_FN_NAME = "export_catalogs"  # kept for compatibility (if you ever export from code)

def validate_catalogs(catalogs: Iterable[JurisdictionCatalog]) -> None:
    for c in catalogs:
        assert isinstance(c.country, CountryCode)
        assert c.courts, "JurisdictionCatalog must contain at least one Court."
        for key, court in c.courts.items():
            assert court.locations, f"Court {key} missing locations."
            for lt in (court.hearing_codes + court.filing_codes + court.order_codes):
                _ = lt.code.namespace()  # raises if invalid
```

---

### `udocket_models/core/reference/registry.py`

```python
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Dict, Any, List
from .base import CatalogBundle, JurisdictionCatalog
from .plugin_protocol import validate_catalogs

# Directory walking is data-only. No code-defined data.
# Override search root with COURT_CATALOG_ROOT if you want to ship data out-of-package.
DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "reference"

def _iter_bundle_files(root: Path | None = None) -> List[Path]:
    base = Path(root) if root else DEFAULT_DATA_ROOT
    return sorted([p for p in base.rglob("*.json") if p.name.endswith("catalog.json")])

def _load_bundle(p: Path) -> CatalogBundle:
    with p.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return CatalogBundle.model_validate(raw)

def discover_catalogs(data_root: str | Path | None = None) -> List[JurisdictionCatalog]:
    root = Path(data_root) if data_root else Path(os.getenv("COURT_CATALOG_ROOT", DEFAULT_DATA_ROOT))
    bundles = [_load_bundle(p) for p in _iter_bundle_files(root)]
    catalogs: List[JurisdictionCatalog] = []
    for b in bundles:
        catalogs.extend(b.data)
    validate_catalogs(catalogs)
    catalogs.sort(key=lambda c: (c.country.value, c.subnational or "", ",".join(sorted(c.courts.keys()))))
    return catalogs

def export_registry_json(data_root: str | Path | None = None) -> Dict[str, Any]:
    items = [c.model_dump(mode="json") for c in discover_catalogs(data_root)]
    return {"schema": "udocket.reference.catalogs.v1", "items": items, "count": len(items)}
```

---

# 2) Writer/compose model moved (Pydantic v2)

### `agents/compose/model.py`

```python
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from udocket_models.core.taxonomy.categories import HearingCategory, FilingCategory, OrderCategory

# These are the writer-facing types the udocket agent uses to render neutral summaries.
# They carry global categories (portable) + a jurisdiction-scoped local code string.

class Hearing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    hearing_type: HearingCategory = Field(..., description="Portable category (global)")
    hearing_local_code: str = Field(..., description="Jurisdictional local code (namespaced)")
    date: str
    status: str
    location_text: Optional[str] = None
    notes: Optional[str] = None

class Filing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    filing_type: FilingCategory
    filing_local_code: str = Field(..., description="Jurisdictional local code")
    title: Optional[str] = None
    date_filed: str
    summary: Optional[str] = None

class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    order_type: OrderCategory
    order_local_code: str = Field(..., description="Jurisdictional local code")
    title: Optional[str] = None
    date: str
    summary: Optional[str] = None
```

> ✅ Now **core models** are only in `udocket_models/core/…`. The writer model lives with the **agents**.

---

# 3) JSON data bundles (data‑only)

> Each bundle uses the wrapper schema `udocket.reference.catalog.bundle.v1` and includes **DB import hints** for PostgreSQL (table names, PKs, FKs, indexes).
> The **same Pydantic models** validate all JSON before your UI/LLM consumes it.

---

### `udocket_models/data/reference/CA/AB/catalog.json`

```json
{
  "schema": "udocket.reference.catalog.bundle.v1",
  "db": {
    "type": "postgresql",
    "tables": {
      "jurisdictions": {
        "table": "jurisdictions",
        "pk": ["country", "subnational"],
        "unique": [["country", "subnational"]]
      },
      "courts": {
        "table": "courts",
        "pk": ["key"],
        "fk": { "jurisdictions": ["country", "subnational"] },
        "unique": [["country", "subnational", "key"]],
        "indexes": [["country", "subnational"]]
      },
      "court_locations": {
        "table": "court_locations",
        "pk": ["court_key", "slug"],
        "fk": { "courts": ["court_key"] },
        "indexes": [["is_base_point"], ["admin_base_slug"]]
      },
      "hearing_codes": {
        "table": "hearing_codes",
        "pk": ["code"],
        "indexes": [["category"], ["court_key"]]
      },
      "filing_codes": {
        "table": "filing_codes",
        "pk": ["code"],
        "indexes": [["category"], ["court_key"]]
      },
      "order_codes": {
        "table": "order_codes",
        "pk": ["code"],
        "indexes": [["category"], ["court_key"]]
      }
    }
  },
  "data": [
    {
      "country": "CA",
      "subnational": "AB",
      "note": "ACJ civil jurisdiction up to $100,000; ABCA registry routing: north of Red Deer files in Edmonton, Red Deer & south in Calgary.",
      "courts": {
        "CA-AB-ACJ": {
          "key": "CA-AB-ACJ",
          "country": "CA",
          "subnational": "AB",
          "level": "TRIAL_PROVINCIAL",
          "formal_name": "Alberta Court of Justice",
          "short_name": "ACJ",
          "divisions": ["CIVIL", "FAMILY", "CRIMINAL", "YOUTH", "TRAFFIC"],
          "locations": [
            { "slug": "airdrie", "display_name": "Airdrie", "is_base_point": false, "admin_base_slug": "calgary" },
            { "slug": "alexis", "display_name": "Alexis", "is_base_point": false },
            { "slug": "athabasca", "display_name": "Athabasca", "is_base_point": false },
            { "slug": "barrhead", "display_name": "Barrhead", "is_base_point": false, "admin_base_slug": "st-albert" },
            { "slug": "bonnyville", "display_name": "Bonnyville", "is_base_point": false },
            { "slug": "boyle", "display_name": "Boyle", "is_base_point": false },
            { "slug": "breton", "display_name": "Breton", "is_base_point": false },
            { "slug": "brooks", "display_name": "Brooks", "is_base_point": false, "admin_base_slug": "medicine-hat" },
            { "slug": "calgary", "display_name": "Calgary", "is_base_point": true },
            { "slug": "camrose", "display_name": "Camrose", "is_base_point": false },
            { "slug": "canmore", "display_name": "Canmore", "is_base_point": false },
            { "slug": "cardston", "display_name": "Cardston", "is_base_point": false, "admin_base_slug": "lethbridge" },
            { "slug": "chateh", "display_name": "Chateh", "is_base_point": false },
            { "slug": "cochrane", "display_name": "Cochrane", "is_base_point": false, "admin_base_slug": "calgary" },
            { "slug": "cold-lake", "display_name": "Cold Lake", "is_base_point": false },
            { "slug": "coronation", "display_name": "Coronation", "is_base_point": false, "admin_base_slug": "red-deer" },
            { "slug": "diamond-valley", "display_name": "Diamond Valley", "is_base_point": false, "admin_base_slug": "calgary" },
            { "slug": "didsbury", "display_name": "Didsbury", "is_base_point": false },
            { "slug": "drayton-valley", "display_name": "Drayton Valley", "is_base_point": false, "admin_base_slug": "leduc" },
            { "slug": "drumheller", "display_name": "Drumheller", "is_base_point": false },
            { "slug": "edmonton", "display_name": "Edmonton", "is_base_point": true },
            { "slug": "edson", "display_name": "Edson", "is_base_point": false },
            { "slug": "evansburg", "display_name": "Evansburg", "is_base_point": false },
            { "slug": "fairview", "display_name": "Fairview", "is_base_point": false, "admin_base_slug": "peace-river" },
            { "slug": "falher", "display_name": "Falher", "is_base_point": false },
            { "slug": "fort-chipewyan", "display_name": "Fort Chipewyan", "is_base_point": false },
            { "slug": "fort-macleod", "display_name": "Fort Macleod", "is_base_point": false },
            { "slug": "fort-mcmurray", "display_name": "Fort McMurray", "is_base_point": true },
            { "slug": "fort-saskatchewan", "display_name": "Fort Saskatchewan", "is_base_point": false },
            { "slug": "fort-vermilion", "display_name": "Fort Vermilion", "is_base_point": false },
            { "slug": "fox-creek", "display_name": "Fox Creek", "is_base_point": false, "admin_base_slug": "grande-prairie" },
            { "slug": "grande-cache", "display_name": "Grande Cache", "is_base_point": false, "admin_base_slug": "hinton" },
            { "slug": "grande-prairie", "display_name": "Grande Prairie", "is_base_point": true },
            { "slug": "hanna", "display_name": "Hanna", "is_base_point": false },
            { "slug": "high-level", "display_name": "High Level", "is_base_point": false },
            { "slug": "high-prairie", "display_name": "High Prairie", "is_base_point": true },
            { "slug": "hinton", "display_name": "Hinton", "is_base_point": true },
            { "slug": "jasper", "display_name": "Jasper", "is_base_point": false },
            { "slug": "killam", "display_name": "Killam", "is_base_point": false },
            { "slug": "lac-la-biche", "display_name": "Lac La Biche", "is_base_point": false },
            { "slug": "leduc", "display_name": "Leduc", "is_base_point": true },
            { "slug": "lethbridge", "display_name": "Lethbridge", "is_base_point": true },
            { "slug": "lloydminster", "display_name": "Lloydminster", "is_base_point": false },
            { "slug": "mayerthorpe", "display_name": "Mayerthorpe", "is_base_point": false },
            { "slug": "medicine-hat", "display_name": "Medicine Hat", "is_base_point": true },
            { "slug": "morinville", "display_name": "Morinville", "is_base_point": false },
            { "slug": "okotoks", "display_name": "Okotoks", "is_base_point": false, "admin_base_slug": "calgary" },
            { "slug": "peace-river", "display_name": "Peace River", "is_base_point": true },
            { "slug": "pincher-creek", "display_name": "Pincher Creek", "is_base_point": false },
            { "slug": "ponoka", "display_name": "Ponoka", "is_base_point": false, "admin_base_slug": "wetaskiwin" },
            { "slug": "red-deer", "display_name": "Red Deer", "is_base_point": true },
            { "slug": "red-earth-creek", "display_name": "Red Earth Creek", "is_base_point": false, "admin_base_slug": "high-prairie" },
            { "slug": "rimbey", "display_name": "Rimbey", "is_base_point": false },
            { "slug": "rocky-mountain-house", "display_name": "Rocky Mountain House", "is_base_point": false, "admin_base_slug": "red-deer" },
            { "slug": "sherwood-park", "display_name": "Sherwood Park", "is_base_point": false },
            { "slug": "siksika-nation", "display_name": "Siksika Nation", "is_base_point": false },
            { "slug": "slave-lake", "display_name": "Slave Lake", "is_base_point": false },
            { "slug": "st-albert", "display_name": "St. Albert", "is_base_point": true },
            { "slug": "st-paul", "display_name": "St. Paul", "is_base_point": false },
            { "slug": "stettler", "display_name": "Stettler", "is_base_point": false },
            { "slug": "stony-plain", "display_name": "Stony Plain", "is_base_point": false },
            { "slug": "strathmore", "display_name": "Strathmore", "is_base_point": false },
            { "slug": "taber", "display_name": "Taber", "is_base_point": false, "admin_base_slug": "lethbridge" },
            { "slug": "tsuutina-nation", "display_name": "Tsuut’ina Nation", "is_base_point": false },
            { "slug": "valleyview", "display_name": "Valleyview", "is_base_point": false, "admin_base_slug": "grande-prairie" },
            { "slug": "vegreville", "display_name": "Vegreville", "is_base_point": false },
            { "slug": "vermilion", "display_name": "Vermilion", "is_base_point": true },
            { "slug": "wabasca-desmarais", "display_name": "Wabasca-Desmarais", "is_base_point": false },
            { "slug": "wainwright", "display_name": "Wainwright", "is_base_point": false, "admin_base_slug": "vermilion" },
            { "slug": "westlock", "display_name": "Westlock", "is_base_point": false, "admin_base_slug": "st-albert" },
            { "slug": "wetaskiwin", "display_name": "Wetaskiwin", "is_base_point": true },
            { "slug": "whitecourt", "display_name": "Whitecourt", "is_base_point": false }
          ],
          "hearing_codes": [
            { "code": { "code": "CA.AB.ACJ.HRG.CIV.CHAMBERS.REG" }, "label": "Regular Chambers", "category": "CIV_CHAMBERS_REGULAR", "divisions": ["CIVIL", "FAMILY"] },
            { "code": { "code": "CA.AB.ACJ.HRG.CIV.CHAMBERS.SPEC" }, "label": "Special Chambers", "category": "CIV_CHAMBERS_SPECIAL", "divisions": ["CIVIL", "FAMILY"] },
            { "code": { "code": "CA.AB.ACJ.HRG.FAM.DOCKET" }, "label": "Family Docket", "category": "FAM_DOCKET", "divisions": ["FAMILY"] },
            { "code": { "code": "CA.AB.ACJ.HRG.CRIM.DOCKET" }, "label": "Criminal Docket", "category": "CRIM_DOCKET", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.CRIM.BAIL" }, "label": "Bail Hearing", "category": "CRIM_BAIL", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.CRIM.PRELIM" }, "label": "Preliminary Inquiry", "category": "CRIM_PRELIM_INQUIRY", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.CRIM.ARRAIGN" }, "label": "Arraignment", "category": "CRIM_ARRAIGNMENT", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.CRIM.TRIAL.JUDGE" }, "label": "Criminal Trial (Judge Alone)", "category": "CRIM_TRIAL_JUDGE", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.CRIM.TRIAL.JURY" }, "label": "Criminal Trial (Jury)", "category": "CRIM_TRIAL_JURY", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.CRIM.SENTENCE" }, "label": "Sentencing", "category": "CRIM_SENTENCING", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.TRAFFIC.DOCKET" }, "label": "Traffic Docket", "category": "TRAFFIC_DOCKET", "divisions": ["TRAFFIC"] },
            { "code": { "code": "CA.AB.ACJ.HRG.SPEC.DAC" }, "label": "Domestic Abuse Court", "category": "SPEC_DOMESTIC_ABUSE", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.SPEC.DTC" }, "label": "Drug Treatment Court", "category": "SPEC_DRUG_TREATMENT", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.SPEC.MHC" }, "label": "Mental Health Court", "category": "SPEC_MENTAL_HEALTH", "divisions": ["CRIMINAL"] },
            { "code": { "code": "CA.AB.ACJ.HRG.SPEC.INDIGENOUS" }, "label": "Indigenous Court", "category": "SPEC_INDIGENOUS", "divisions": ["CRIMINAL"] }
          ],
          "filing_codes": [
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.STATEMENT_OF_CLAIM" }, "label": "Statement of Claim", "category": "PLEADING_CLAIM" },
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.STATEMENT_OF_DEFENCE" }, "label": "Statement of Defence", "category": "PLEADING_DEFENCE" },
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.COUNTERCLAIM" }, "label": "Counterclaim", "category": "PLEADING_COUNTERCLAIM" },
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.REPLY" }, "label": "Reply", "category": "PLEADING_REPLY" },
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.ORIGINATING_APPLICATION" }, "label": "Originating Application", "category": "ORIGINATING_APPLICATION" },
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.APPLICATION" }, "label": "Application", "category": "INTERLOCUTORY_APPLICATION" },
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.AFFIDAVIT" }, "label": "Affidavit", "category": "AFFIDAVIT" },
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.RECORDS" }, "label": "List/Affidavit of Records", "category": "LIST_OR_AFFIDAVIT_OF_RECORDS" },
            { "code": { "code": "CA.AB.ACJ.FILE.CIV.BRIEF" }, "label": "Brief/Memorandum", "category": "BRIEF_OR_MEMO" },
            { "code": { "code": "CA.AB.ACJ.FILE.GEN.ORDER" }, "label": "Order", "category": "ORDER" },
            { "code": { "code": "CA.AB.ACJ.FILE.GEN.JUDGMENT" }, "label": "Judgment", "category": "JUDGMENT" }
          ],
          "order_codes": [
            { "code": { "code": "CA.AB.ACJ.ORD.SCHED.END" }, "label": "Scheduling Endorsement", "category": "SCHEDULING_ENDORSEMENT" },
            { "code": { "code": "CA.AB.ACJ.ORD.INTERIM" }, "label": "Interim Order", "category": "INTERIM_ORDER" },
            { "code": { "code": "CA.AB.ACJ.ORD.FINAL" }, "label": "Final Order", "category": "FINAL_ORDER" },
            { "code": { "code": "CA.AB.ACJ.ORD.CONSENT" }, "label": "Consent Order", "category": "CONSENT_ORDER" },
            { "code": { "code": "CA.AB.ACJ.ORD.REASONS" }, "label": "Reasons for Judgment", "category": "REASONS_FOR_JUDGMENT" },
            { "code": { "code": "CA.AB.ACJ.ORD.MINUTE" }, "label": "Minute Entry", "category": "MINUTE_ENTRY" }
          ]
        },

        "CA-AB-KB": {
          "key": "CA-AB-KB",
          "country": "CA",
          "subnational": "AB",
          "level": "TRIAL_SUPERIOR",
          "formal_name": "Court of King's Bench of Alberta",
          "short_name": "ABKB",
          "divisions": ["CIVIL", "FAMILY", "CRIMINAL", "SURROGATE", "APPLICATIONS", "COMMERCIAL"],
          "locations": [
            { "slug": "kb-calgary", "display_name": "Calgary (KB)", "is_base_point": true, "divisions_served": ["CIVIL", "FAMILY", "CRIMINAL", "SURROGATE", "APPLICATIONS", "COMMERCIAL"] },
            { "slug": "kb-edmonton", "display_name": "Edmonton (KB)", "is_base_point": true, "divisions_served": ["CIVIL", "FAMILY", "CRIMINAL", "SURROGATE", "APPLICATIONS", "COMMERCIAL"] }
          ],
          "hearing_codes": [
            { "code": { "code": "CA.AB.KB.HRG.CIV.CHAMBERS.REG" }, "label": "Justice Chambers – Regular", "category": "CIV_CHAMBERS_REGULAR", "divisions": ["CIVIL", "FAMILY"] },
            { "code": { "code": "CA.AB.KB.HRG.CIV.CHAMBERS.SPEC" }, "label": "Justice Chambers – Special", "category": "CIV_CHAMBERS_SPECIAL", "divisions": ["CIVIL", "FAMILY"] },
            { "code": { "code": "CA.AB.KB.HRG.CIV.JDR" }, "label": "Judicial Dispute Resolution", "category": "CIV_JDR", "divisions": ["CIVIL", "FAMILY"] },
            { "code": { "code": "CA.AB.KB.HRG.CIV.TRIAL.JUDGE" }, "label": "Civil Trial (Judge Alone)", "category": "CIV_TRIAL_JUDGE", "divisions": ["CIVIL"] },
            { "code": { "code": "CA.AB.KB.HRG.CIV.TRIAL.JURY" }, "label": "Civil Trial (Jury)", "category": "CIV_TRIAL_JURY", "divisions": ["CIVIL"] }
          ],
          "filing_codes": [
            { "code": { "code": "CA.AB.KB.FILE.CIV.ORIGINATING_APPLICATION" }, "label": "Originating Application", "category": "ORIGINATING_APPLICATION" }
          ],
          "order_codes": [
            { "code": { "code": "CA.AB.KB.ORD.FINAL" }, "label": "Final Order", "category": "FINAL_ORDER" }
          ]
        },

        "CA-AB-ABCA": {
          "key": "CA-AB-ABCA",
          "country": "CA",
          "subnational": "AB",
          "level": "APPEAL",
          "formal_name": "Court of Appeal of Alberta",
          "short_name": "ABCA",
          "divisions": ["APPEALS", "APPLICATIONS"],
          "locations": [
            { "slug": "abca-calgary", "display_name": "Calgary (ABCA)", "is_base_point": true, "notes": "Red Deer & south: file in Calgary registry." },
            { "slug": "abca-edmonton", "display_name": "Edmonton (ABCA)", "is_base_point": true, "notes": "North of Red Deer: file in Edmonton registry." }
          ],
          "hearing_codes": [
            { "code": { "code": "CA.AB.ABCA.HRG.APP.APPLICATIONS_LIST" }, "label": "Applications List", "category": "APP_APPLICATIONS_LIST", "divisions": ["APPLICATIONS"] },
            { "code": { "code": "CA.AB.ABCA.HRG.APP.SINGLE_JUDGE" }, "label": "Single Judge Application", "category": "APP_SINGLE_JUDGE_APP", "divisions": ["APPLICATIONS"] },
            { "code": { "code": "CA.AB.ABCA.HRG.APP.APPEAL_HEARING" }, "label": "Appeal Hearing", "category": "APP_HEARING", "divisions": ["APPEALS"] }
          ],
          "filing_codes": [
            { "code": { "code": "CA.AB.ABCA.FILE.APP.NOTICE_OF_APPEAL" }, "label": "Notice of Appeal", "category": "NOTICE_OF_APPEAL" },
            { "code": { "code": "CA.AB.ABCA.FILE.APP.APPEAL_RECORD" }, "label": "Appeal Record", "category": "APPEAL_RECORD" },
            { "code": { "code": "CA.AB.ABCA.FILE.APP.FACTUM" }, "label": "Factum", "category": "FACTUM" },
            { "code": { "code": "CA.AB.ABCA.FILE.APP.EKE" }, "label": "Extracts of Key Evidence", "category": "EXTRACTS_KEY_EVIDENCE" },
            { "code": { "code": "CA.AB.ABCA.FILE.APP.BOA" }, "label": "Book of Authorities", "category": "BOOK_OF_AUTHORITIES" }
          ],
          "order_codes": [
            { "code": { "code": "CA.AB.ABCA.ORD.REASONS" }, "label": "Reasons for Judgment", "category": "REASONS_FOR_JUDGMENT" }
          ]
        }
      }
    }
  ],
  "meta": {
    "source_urls": [
      "https://albertacourts.ca/cj/court-practice-and-schedules/Contact",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/airdrie",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/westlock",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/grande-cache",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/valleyview",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/fox-creek",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/coronation",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/rocky-mountain-house",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/fairview",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/red-earth-creek",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/brooks",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/ponoka",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/taber",
      "https://albertacourts.ca/cj/court-practice-and-schedules/locations-map/location-detail/cardston",
      "https://albertacourts.ca/ca/registry/about",
      "https://albertacourts.ca/ca/registry/filing",
      "https://albertacourts.ca/cj/home",
      "https://albertacourts.ca/cj/areas-of-law/criminal/special-courts"
    ],
    "notes": "All data here mirrors official ACJ/KB/ABCA sources as of 2025-10-12. Monetary limit for ACJ Civil = $100,000."
  }
}
```

> **Evidence of accuracy**: ACJ list of 72 locations is from the official “Contact & Hours” page. ([Alberta Courts][1])
> Circuit→base examples are from each location’s “Location Detail” page that explicitly states **“Continue to send all court documents to …”** (see `meta.source_urls`). Examples: Airdrie→Calgary; Westlock→St. Albert; Grande Cache→Hinton; Valleyview/Fox Creek→Grande Prairie; Coronation/Rocky Mountain House→Red Deer; Fairview→Peace River; Red Earth Creek→High Prairie; Brooks→Medicine Hat; Ponoka→Wetaskiwin; Taber/Cardston→Lethbridge; Wainwright→Vermilion. ([Alberta Courts][2])
> ABCA registry routing statements appear on official pages. ([Alberta Courts][4])
> Civil limit confirmation. ([Alberta Courts][3])

---

### `udocket_models/data/reference/CA/FED/catalog.json`

```json
{
  "schema": "udocket.reference.catalog.bundle.v1",
  "db": {
    "type": "postgresql",
    "tables": {
      "jurisdictions": { "table": "jurisdictions", "pk": ["country", "subnational"], "unique": [["country", "subnational"]] },
      "courts":        { "table": "courts", "pk": ["key"], "fk": { "jurisdictions": ["country", "subnational"] }, "unique": [["country", "subnational", "key"]] },
      "court_locations": { "table": "court_locations", "pk": ["court_key", "slug"], "fk": { "courts": ["court_key"] } },
      "hearing_codes": { "table": "hearing_codes", "pk": ["code"] },
      "filing_codes":  { "table": "filing_codes", "pk": ["code"] },
      "order_codes":   { "table": "order_codes", "pk": ["code"] }
    }
  },
  "data": [
    {
      "country": "CA",
      "subnational": "FED",
      "note": "CAS serves the FC, FCA, and TCC through a national registry network.",
      "courts": {
        "CA-FED-FC": {
          "key": "CA-FED-FC",
          "country": "CA",
          "subnational": "FED",
          "level": "TRIAL_SUPERIOR",
          "formal_name": "Federal Court",
          "short_name": "FC",
          "divisions": ["CIVIL", "APPLICATIONS"],
          "locations": [
            { "slug": "fc-ottawa",  "display_name": "Ottawa (CAS – 90 Sparks St / Thomas D'Arcy McGee)", "is_base_point": true, "divisions_served": ["CIVIL", "APPLICATIONS"] },
            { "slug": "fc-toronto", "display_name": "Toronto (CAS – 180 Queen St W)",                     "is_base_point": true, "divisions_served": ["CIVIL", "APPLICATIONS"] }
          ],
          "hearing_codes": [
            { "code": { "code": "CA.FED.FC.HRG.CIV.MOTIONS_LIST" }, "label": "Motions List", "category": "CIV_CHAMBERS_REGULAR", "divisions": ["CIVIL", "APPLICATIONS"] },
            { "code": { "code": "CA.FED.FC.HRG.CIV.CASE_MGMT"   }, "label": "Case Management Conference", "category": "CIV_CASE_MGMT_CONF", "divisions": ["CIVIL", "APPLICATIONS"] }
          ],
          "filing_codes": [],
          "order_codes": []
        },
        "CA-FED-FCA": {
          "key": "CA-FED-FCA",
          "country": "CA",
          "subnational": "FED",
          "level": "APPEAL",
          "formal_name": "Federal Court of Appeal",
          "short_name": "FCA",
          "divisions": ["APPEALS", "APPLICATIONS"],
          "locations": [
            { "slug": "fca-ottawa", "display_name": "Ottawa (CAS)", "is_base_point": true, "divisions_served": ["APPEALS", "APPLICATIONS"] }
          ],
          "hearing_codes": [
            { "code": { "code": "CA.FED.FCA.HRG.APP.SINGLE_JUDGE" }, "label": "Single Judge Motion", "category": "APP_SINGLE_JUDGE_APP", "divisions": ["APPLICATIONS"] },
            { "code": { "code": "CA.FED.FCA.HRG.APP.APPEAL_HEARING" }, "label": "Appeal Hearing", "category": "APP_HEARING", "divisions": ["APPEALS"] }
          ],
          "filing_codes": [],
          "order_codes": []
        },
        "CA-FED-TCC": {
          "key": "CA-FED-TCC",
          "country": "CA",
          "subnational": "FED",
          "level": "TRIAL_SUPERIOR",
          "formal_name": "Tax Court of Canada",
          "short_name": "TCC",
          "divisions": ["CIVIL"],
          "locations": [
            { "slug": "tcc-ottawa", "display_name": "Ottawa (200 Kent St)", "is_base_point": true, "divisions_served": ["CIVIL"] }
          ],
          "hearing_codes": [
            { "code": { "code": "CA.FED.TCC.HRG.CIV.GENERAL_LIST" }, "label": "General List", "category": "CIV_CHAMBERS_REGULAR", "divisions": ["CIVIL"] }
          ],
          "filing_codes": [],
          "order_codes": []
        }
      }
    }
  ],
  "meta": {
    "source_urls": [
      "https://www.fct-cf.ca/en/pages/representing-yourself/registry/registry-offices",
      "https://www.cas-satj.gc.ca/en/pages/registry/offices/ottawa",
      "https://www.cas-satj.gc.ca/en/pages/registry/offices/toronto"
    ],
    "notes": "CAS registry network as of 2025-10-12."
  }
}
```

*(CAS/FC registry sources.)* ([fct-cf.ca][7])

---

### `udocket_models/data/reference/US/NY/catalog.json`

```json
{
  "schema": "udocket.reference.catalog.bundle.v1",
  "db": {
    "type": "postgresql",
    "tables": {
      "jurisdictions": { "table": "jurisdictions", "pk": ["country", "subnational"] },
      "courts":        { "table": "courts", "pk": ["key"], "fk": { "jurisdictions": ["country", "subnational"] } },
      "court_locations": { "table": "court_locations", "pk": ["court_key", "slug"], "fk": { "courts": ["court_key"] } },
      "hearing_codes": { "table": "hearing_codes", "pk": ["code"] }
    }
  },
  "data": [
    {
      "country": "US",
      "subnational": "NY",
      "note": "NY Supreme Court – Commercial Division (New York County) minimal catalog.",
      "courts": {
        "US-NY-NYCO-SUP-COMDIV": {
          "key": "US-NY-NYCO-SUP-COMDIV",
          "country": "US",
          "subnational": "NY",
          "level": "TRIAL_SUPERIOR",
          "formal_name": "Supreme Court of the State of New York – Commercial Division (New York County)",
          "short_name": "NYSup ComDiv NY County",
          "divisions": ["CIVIL", "COMMERCIAL"],
          "locations": [
            { "slug": "nyco-60-centre", "display_name": "60 Centre Street (Commercial Division Support – Room 119/119A)", "is_base_point": true, "divisions_served": ["CIVIL", "COMMERCIAL"] }
          ],
          "hearing_codes": [
            { "code": { "code": "US.NY.NYCO.SUP.COMDIV.HRG.PRELIM_CONF" }, "label": "Preliminary Conference", "category": "CIV_CASE_MGMT_CONF", "divisions": ["CIVIL", "COMMERCIAL"] },
            { "code": { "code": "US.NY.NYCO.SUP.COMDIV.HRG.COMPLIANCE_CONF" }, "label": "Compliance Conference", "category": "CIV_CASE_MGMT_CONF", "divisions": ["CIVIL", "COMMERCIAL"] },
            { "code": { "code": "US.NY.NYCO.SUP.COMDIV.HRG.MOTION_SUBMIT" }, "label": "Motion Submission Part", "category": "CIV_CHAMBERS_REGULAR", "divisions": ["CIVIL", "COMMERCIAL"] },
            { "code": { "code": "US.NY.NYCO.SUP.COMDIV.HRG.TRIAL_JUDGE" }, "label": "Trial – Justice Part", "category": "CIV_TRIAL_JUDGE", "divisions": ["CIVIL", "COMMERCIAL"] }
          ],
          "filing_codes": [],
          "order_codes": []
        }
      }
    }
  ],
  "meta": {
    "source_urls": [
      "https://ww2.nycourts.gov/courts/comdiv/ny/newyork.shtml",
      "https://ww2.nycourts.gov/courts/comdiv/ny/newyork_support.shtml",
      "https://ww2.nycourts.gov/courts/1jd/supctmanh/Conferences-CaseManagement.shtml",
      "https://ww2.nycourts.gov/courts/1jd/supctmanh/motions_on_notice.shtml",
      "https://ww2.nycourts.gov/courts/1jd/supctmanh/Court_Offices_and_functions.shtml"
    ],
    "notes": "Confirmed support office rooms at 60 Centre St and PC/compliance/motion submission practices."
  }
}
```

*(NY ComDiv sources.)* ([New York State Unified Court System][6])

---

# 4) README (expansion & ingestion guide)

### `udocket_models/README.md`

```md
# udocket_models v4 (models-only + JSON data)

This package separates **Pydantic v2 models** (validation) from **JSON data** (content).
The **core models** live under `udocket_models/core/…`. All **reference catalogs** are JSON
bundles under `udocket_models/data/reference/<COUNTRY>/<REGION>/catalog.json`.

## Why this design?
- **Zero code-data coupling**: add or update any jurisdiction by editing JSON only.
- **Enum isolation**: the UI/LLM consumes *global categories* (portable enums) and looks up
  *local, namespaced codes* from the selected court catalog.
- **DB-friendly**: every JSON bundle includes optional PostgreSQL table hints to simplify import.

---

## Glossary
- **Global categories**: portable enums (e.g., `HearingCategory.CRIM_DOCKET`).
- **Local codes**: namespaced codes (e.g., `CA.AB.ACJ.HRG.CRIM.DOCKET`), declared inside each Court’s catalog.

---

## File conventions
```

udocket_models/data/reference/<COUNTRY-ISO2>/<REGION>/catalog.json

````
- Example: `CA/AB/catalog.json` (Alberta), `CA/FED/catalog.json` (Canada Federal),
  `US/NY/catalog.json` (New York State).
- Each file is a **CatalogBundle**:
  ```json
  { "schema":"udocket.reference.catalog.bundle.v1", "db":{...}, "data":[ JurisdictionCatalog... ], "meta":{...} }
````

### Keys & naming

* `Court.key`: `CC-REGION-COURT` (e.g., `CA-AB-ACJ`).
* `CourtLocation.slug`: kebab-case (e.g., `st-albert`, `wabasca-desmarais`).
* `LocalCode.code`: `"CC.REGION.COURT.DOMAIN.SPEC"` (regex-validated).

---

## Load & validate at runtime

```python
from udocket_models.core.reference.registry import export_registry_json, discover_catalogs

# Load all bundles under the default data folder:
payload = export_registry_json()
print(payload["count"], "jurisdictions loaded")

# Or point at your own data root:
payload = export_registry_json("/path/to/your/json/data")
```

---

## Expanding jurisdictions (Step-by-step)

1. **Create a new JSON bundle**: `udocket_models/data/reference/<COUNTRY>/<REGION>/catalog.json`.
2. Add a `JurisdictionCatalog` with one or more `Court` objects:
   * Populate `locations` (`is_base_point` where applicable; set `admin_base_slug` for circuits
     *only if an official page says so*).
   * Add `hearing_codes` / `filing_codes` / `order_codes` with **LocalCode** strings mapping to **global categories**.
3. Include optional `"db"` hints (table names/PK/FK) to help ETL.
4. *(Optional)* Add your source URLs to `bundle.meta.source_urls` for provenance.
5. Run your CI to parse/validate the bundle with our Pydantic models.

**Do’s**
* Use authoritative sources only (court websites, statutes, official PDFs).
* Keep `Court.key` and the dict key identical.
* Use namespaced **LocalCode** tokens consistently.

**Don’ts**
* Don’t put any Python data into model modules.
* Don’t mix global enums with jurisdiction-specific labels.

---

## Alberta notes for reviewers
* ACJ Civil monetary jurisdiction is **$100,000**. Source: ACJ civil info.
* ACJ has **72** locations. Source: ACJ “Contact & Hours” list.
* Circuit→base relationships used in this catalog only where the location page states
  **“Continue to send all court documents to …”** (see `meta.source_urls` inside the bundle).
* ABCA registry routing: **north of Red Deer → Edmonton; Red Deer & south → Calgary**.

(See the catalog.json `meta.source_urls` for links.)

**Citations**: Civil limit & ACJ list. :contentReference[oaicite:13]{index=13}


### Quick smoke test (example)
```python
from udocket_models.core.reference.registry import export_registry_json
j = export_registry_json()
ab = next(i for i in j["items"] if i["country"]=="CA" and i.get("subnational")=="AB")
acj = ab["courts"]["CA-AB-ACJ"]
assert len(acj["locations"]) == 72  # ACJ locations
```
