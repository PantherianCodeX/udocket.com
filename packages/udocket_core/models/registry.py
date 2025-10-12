# filename: udocket_models/registry.py
from __future__ import annotations
from typing import Dict, Tuple, Optional
from .core import UBase
from .enums import CountryEnum
from .reference.ca_ab import AlbertaCourtCatalog
from .reference.ca_federal import CanadaFederalCatalog
from .reference.us_ny import NewYorkCourtCatalog

JurisdictionKey = Tuple[str, str]  # (country, subnational)

class CourtRegistry(UBase):
    catalogs: Dict[JurisdictionKey, UBase] = {}

    @classmethod
    def bootstrap(cls) -> "CourtRegistry":
        reg = cls()
        reg.catalogs[(CountryEnum.CA.value, "AB")] = AlbertaCourtCatalog.make()
        reg.catalogs[(CountryEnum.CA.value, "FED")] = CanadaFederalCatalog.make()
        reg.catalogs[(CountryEnum.US.value, "NY")] = NewYorkCourtCatalog.make()
        return reg

    def get(self, country: str, subnational: str) -> Optional[UBase]:
        return self.catalogs.get((country, subnational))
