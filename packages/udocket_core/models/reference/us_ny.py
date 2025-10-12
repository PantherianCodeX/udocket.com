# filename: udocket_models/reference/us_ny.py
from __future__ import annotations
from ..core import UBase
from ..enums import CountryEnum, CourtLevelEnum, CourtDivisionEnum, LanguageEnum, HearingTypeEnum, FilingTypeEnum, OrderTypeEnum
from .ca_ab import Court, CourtLocation

class NewYorkCourtCatalog(UBase):
    country: CountryEnum = CountryEnum.US
    subnational: str = "NY"

    # minimal coverage for expansion
    court_of_appeals: Court
    appellate_division: Court
    supreme_court_statewide: Court
    # Fully populated example branch: NY County Supreme Court (Commercial Division)
    ny_county_commercial_division: Court

    @staticmethod
    def make() -> "NewYorkCourtCatalog":
        court_of_appeals = Court(
            key="NY_COURT_OF_APPEALS",
            level=CourtLevelEnum.SUPREME_NATIONAL,  # state highest
            formal_name="New York Court of Appeals",
            short_name="NYCOA",
            divisions=[CourtDivisionEnum.APPEALS],
            primary_languages=[LanguageEnum.en],
            locations=[CourtLocation(name="Albany", city="Albany", is_base_point=True)],
            hearing_types=[HearingTypeEnum.NY_TRIAL],  # placeholder for argument sessions
            filing_types=[FilingTypeEnum.NOTICE_OF_APPEAL, FilingTypeEnum.BRIEF_OR_MEMORANDUM, FilingTypeEnum.TRANSCRIPT],
            order_types=[OrderTypeEnum.REASONS_FOR_JUDGMENT, OrderTypeEnum.FINAL_ORDER]
        )

        appellate_division = Court(
            key="NY_APPELLATE_DIVISION",
            level=CourtLevelEnum.APPEAL,
            formal_name="Appellate Division of the Supreme Court (First–Fourth Depts.)",
            short_name="AD",
            divisions=[CourtDivisionEnum.APPEALS],
            primary_languages=[LanguageEnum.en],
            locations=[
                CourtLocation(name="First Department", city="New York"),
                CourtLocation(name="Second Department", city="Brooklyn"),
                CourtLocation(name="Third Department", city="Albany"),
                CourtLocation(name="Fourth Department", city="Rochester"),
            ],
            hearing_types=[HearingTypeEnum.NY_TRIAL],  # argument calendars
            filing_types=[FilingTypeEnum.NOTICE_OF_APPEAL, FilingTypeEnum.APPEAL_RECORD, FilingTypeEnum.BRIEF_OR_MEMORANDUM],
            order_types=[OrderTypeEnum.FINAL_ORDER, OrderTypeEnum.REASONS_FOR_JUDGMENT]
        )

        supreme_statewide = Court(
            key="NY_SUPREME_COURT",
            level=CourtLevelEnum.TRIAL_SUPERIOR,
            formal_name="Supreme Court of the State of New York",
            short_name="NYSupCt",
            divisions=[CourtDivisionEnum.CIVIL, CourtDivisionEnum.CRIMINAL, CourtDivisionEnum.COMMERCIAL_LIST],
            primary_languages=[LanguageEnum.en],
            locations=[CourtLocation(name="Statewide (62 counties)", city="Statewide")],
            hearing_types=[HearingTypeEnum.NY_IAS_MOTION, HearingTypeEnum.NY_PRELIMINARY_CONFERENCE, HearingTypeEnum.NY_COMPLIANCE_CONFERENCE, HearingTypeEnum.NY_TRIAL],
            filing_types=[FilingTypeEnum.BRIEF_OR_MEMORANDUM, FilingTypeEnum.ORDER, FilingTypeEnum.TRANSCRIPT],
            order_types=[OrderTypeEnum.INTERIM_ORDER, OrderTypeEnum.FINAL_ORDER, OrderTypeEnum.REASONS_FOR_JUDGMENT]
        )

        # Fully populated branch: NY County (Manhattan) – Commercial Division at 60 Centre St.
        nyc_cd = Court(
            key="NY_SUPREME_NY_COUNTY_COMMERCIAL_DIVISION",
            level=CourtLevelEnum.TRIAL_SUPERIOR,
            formal_name="Supreme Court, New York County – Commercial Division",
            short_name="NYCD-NY",
            divisions=[CourtDivisionEnum.COMMERCIAL_LIST],
            primary_languages=[LanguageEnum.en],
            locations=[
                CourtLocation(name="60 Centre Street", city="New York", is_base_point=True,
                              notes="Commercial Division Support Office Room 119A; NYSCEF e-filing.")
            ],
            hearing_types=[HearingTypeEnum.NY_IAS_MOTION, HearingTypeEnum.NY_PRELIMINARY_CONFERENCE,
                           HearingTypeEnum.NY_COMPLIANCE_CONFERENCE, HearingTypeEnum.NY_TRIAL],
            filing_types=[FilingTypeEnum.BRIEF_OR_MEMORANDUM, FilingTypeEnum.ORDER, FilingTypeEnum.TRANSCRIPT],
            order_types=[OrderTypeEnum.INTERIM_ORDER, OrderTypeEnum.FINAL_ORDER, OrderTypeEnum.REASONS_FOR_JUDGMENT]
        )
        # 

        return NewYorkCourtCatalog(
            court_of_appeals=court_of_appeals,
            appellate_division=appellate_division,
            supreme_court_statewide=supreme_statewide,
            ny_county_commercial_division=nyc_cd
        )
