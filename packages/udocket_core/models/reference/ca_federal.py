# filename: udocket_models/reference/ca_federal.py
from __future__ import annotations
from ..core import UBase
from ..enums import CountryEnum, CourtLevelEnum, CourtDivisionEnum, LanguageEnum, HearingTypeEnum, FilingTypeEnum, OrderTypeEnum
from .ca_ab import Court, CourtLocation

class CanadaFederalCatalog(UBase):
    country: CountryEnum = CountryEnum.CA
    subnational: str = "FED"  # label used by registry

    federal_court: Court
    federal_court_of_appeal: Court

    @staticmethod
    def make() -> "CanadaFederalCatalog":
        registries = [
            CourtLocation(name="Ottawa (Principal Registry)", city="Ottawa", is_base_point=True),
            CourtLocation(name="Vancouver", city="Vancouver"),
            CourtLocation(name="Calgary", city="Calgary"),
            CourtLocation(name="Edmonton", city="Edmonton"),
            CourtLocation(name="Winnipeg", city="Winnipeg"),
            CourtLocation(name="Toronto", city="Toronto"),
            CourtLocation(name="Montreal", city="Montreal"),
            CourtLocation(name="Halifax", city="Halifax"),
            CourtLocation(name="St. John’s", city="St. John’s"),
        ]
        # 

        fc = Court(
            key="FEDERAL_COURT_OF_CANADA",
            level=CourtLevelEnum.TRIAL_SUPERIOR,
            formal_name="Federal Court",
            short_name="FC",
            divisions=[CourtDivisionEnum.CIVIL, CourtDivisionEnum.ADMINISTRATIVE, CourtDivisionEnum.IMMIGRATION, CourtDivisionEnum.TAX],
            primary_languages=[LanguageEnum.en, LanguageEnum.fr],
            locations=registries,
            hearing_types=[HearingTypeEnum.FC_MOTION, HearingTypeEnum.FC_TRIAL],
            filing_types=[FilingTypeEnum.APPLICATION, FilingTypeEnum.AFFIDAVIT, FilingTypeEnum.BRIEF_OR_MEMORANDUM, FilingTypeEnum.TRANSCRIPT, FilingTypeEnum.ORDER],
            order_types=[OrderTypeEnum.INTERIM_ORDER, OrderTypeEnum.FINAL_ORDER, OrderTypeEnum.REASONS_FOR_JUDGMENT]
        )

        fca = Court(
            key="FEDERAL_COURT_OF_APPEAL",
            level=CourtLevelEnum.APPEAL,
            formal_name="Federal Court of Appeal",
            short_name="FCA",
            divisions=[CourtDivisionEnum.APPEALS],
            primary_languages=[LanguageEnum.en, LanguageEnum.fr],
            locations=[registries[0]] + registries[1:],  # same network
            hearing_types=[HearingTypeEnum.FCA_APPEAL_HEARING],
            filing_types=[FilingTypeEnum.NOTICE_OF_APPEAL, FilingTypeEnum.APPEAL_RECORD, FilingTypeEnum.FACTUM, FilingTypeEnum.BOOK_OF_AUTHORITIES],
            order_types=[OrderTypeEnum.REASONS_FOR_JUDGMENT, OrderTypeEnum.INTERIM_ORDER, OrderTypeEnum.FINAL_ORDER]
        )

        return CanadaFederalCatalog(federal_court=fc, federal_court_of_appeal=fca)
