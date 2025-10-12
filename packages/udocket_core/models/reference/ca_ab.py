# filename: udocket_models/reference/ca_ab.py
from __future__ import annotations
from typing import List, Optional
from pydantic import Field
from ..core import UBase
from ..enums import (
    CountryEnum, CourtLevelEnum, CourtDivisionEnum, LanguageEnum,
    HearingTypeEnum, FilingTypeEnum, OrderTypeEnum
)

class CourtLocation(UBase):
    name: str
    city: str
    is_base_point: bool = False
    admin_base: Optional[str] = Field(default=None, description="If circuit, which base point administers")
    notes: Optional[str] = None

class Court(UBase):
    key: str                         # e.g., "ALBERTA_COURT_OF_JUSTICE"
    level: CourtLevelEnum
    formal_name: str                 # UI display name
    short_name: str                  # e.g., "ACJ", "KB", "ABCA"
    divisions: List[CourtDivisionEnum]
    primary_languages: List[LanguageEnum] = [LanguageEnum.en]
    locations: List[CourtLocation]
    hearing_types: List[HearingTypeEnum]
    filing_types: List[FilingTypeEnum]
    order_types: List[OrderTypeEnum]

class AlbertaCourtCatalog(UBase):
    """Authoritative Alberta court system reference for udocket."""
    country: CountryEnum = CountryEnum.CA
    subnational: str = "AB"

    # Alberta Court of Justice (trial-provincial)
    acj: Court
    # Court of King's Bench (superior trial)
    kb: Court
    # Court of Appeal
    abca: Court

    @staticmethod
    def make() -> "AlbertaCourtCatalog":
        # ---- Court of King's Bench base locations (13) ----
        kb_locations = [
            CourtLocation(name="Calgary", city="Calgary", is_base_point=True),
            CourtLocation(name="Drumheller", city="Drumheller", is_base_point=True),
            CourtLocation(name="Edmonton", city="Edmonton", is_base_point=True),
            CourtLocation(name="Fort McMurray", city="Fort McMurray", is_base_point=True),
            CourtLocation(name="Grande Prairie", city="Grande Prairie", is_base_point=True),
            CourtLocation(name="High Level", city="High Level", is_base_point=True),
            CourtLocation(name="Hinton", city="Hinton", is_base_point=True),
            CourtLocation(name="Lethbridge", city="Lethbridge", is_base_point=True),
            CourtLocation(name="Medicine Hat", city="Medicine Hat", is_base_point=True),
            CourtLocation(name="Peace River", city="Peace River", is_base_point=True),
            CourtLocation(name="Red Deer", city="Red Deer", is_base_point=True),
            CourtLocation(name="St. Paul", city="St. Paul", is_base_point=True),
            CourtLocation(name="Wetaskiwin", city="Wetaskiwin", is_base_point=True),
        ]
        # 

        kb_hearings = [
            HearingTypeEnum.JUSTICE_CHAMBERS_REGULAR,
            HearingTypeEnum.JUSTICE_CHAMBERS_SPECIAL,
            HearingTypeEnum.APPLICATIONS_JUDGE_REGULAR,
            HearingTypeEnum.APPLICATIONS_JUDGE_SPECIAL,
            HearingTypeEnum.CASE_MANAGEMENT_CONFERENCE,
            HearingTypeEnum.PRE_TRIAL_CONFERENCE,
            HearingTypeEnum.CIVIL_JDR,
            HearingTypeEnum.ASSESSMENT_OF_COSTS,
            HearingTypeEnum.TRIAL_CIVIL_JUDGE_ALONE,
            HearingTypeEnum.TRIAL_CIVIL_JURY,
        ]

        # ---- Alberta Court of Justice locations (base + circuits) ----
        # Source: 'Contact & Hours' location list and location-detail pages; Court sits at ~72 points. 
        # (Examples below include base/circuit pointers commonly used operationally.)
        acj_locations = [
            CourtLocation(name="Calgary", city="Calgary", is_base_point=True),
            CourtLocation(name="Edmonton", city="Edmonton", is_base_point=True),
            CourtLocation(name="Red Deer", city="Red Deer", is_base_point=True),
            CourtLocation(name="Lethbridge", city="Lethbridge", is_base_point=True),
            CourtLocation(name="Medicine Hat", city="Medicine Hat", is_base_point=True),
            CourtLocation(name="Fort McMurray", city="Fort McMurray", is_base_point=True),
            CourtLocation(name="Grande Prairie", city="Grande Prairie", is_base_point=True),
            CourtLocation(name="Peace River", city="Peace River", is_base_point=True),
            CourtLocation(name="St. Paul", city="St. Paul", is_base_point=True),
            CourtLocation(name="Wetaskiwin", city="Wetaskiwin", is_base_point=True),
            CourtLocation(name="Hinton", city="Hinton", is_base_point=True),
            CourtLocation(name="High Level", city="High Level", is_base_point=True),
            CourtLocation(name="High Prairie", city="High Prairie", is_base_point=True),
            CourtLocation(name="Slave Lake", city="Slave Lake", is_base_point=True),
            # circuits (selection shown; list reflects the official Contact & Hours page)
            CourtLocation(name="Airdrie", city="Airdrie", admin_base="Calgary"),
            CourtLocation(name="Alexis", city="Alexis", admin_base="Stony Plain"),
            CourtLocation(name="Athabasca", city="Athabasca", admin_base="St. Albert"),
            CourtLocation(name="Barrhead", city="Barrhead", admin_base="Stony Plain"),
            CourtLocation(name="Bonnyville", city="Bonnyville", admin_base="St. Paul"),
            CourtLocation(name="Boyle", city="Boyle", admin_base="St. Albert"),
            CourtLocation(name="Breton", city="Breton", admin_base="Wetaskiwin"),
            CourtLocation(name="Brooks", city="Brooks", admin_base="Medicine Hat"),
            CourtLocation(name="Camrose", city="Camrose", admin_base="Wetaskiwin"),
            CourtLocation(name="Canmore", city="Canmore", admin_base="Calgary"),
            CourtLocation(name="Cardston", city="Cardston", admin_base="Lethbridge"),
            CourtLocation(name="Chateh", city="Chateh", admin_base="High Level"),
            CourtLocation(name="Cochrane", city="Cochrane", admin_base="Calgary"),
            CourtLocation(name="Cold Lake", city="Cold Lake", admin_base="St. Paul"),
            CourtLocation(name="Coronation", city="Coronation", admin_base="Stettler"),
            CourtLocation(name="Diamond Valley", city="Diamond Valley", admin_base="Calgary"),
            CourtLocation(name="Didsbury", city="Didsbury", admin_base="Calgary"),
            CourtLocation(name="Drayton Valley", city="Drayton Valley", admin_base="Wetaskiwin"),
            CourtLocation(name="Drumheller", city="Drumheller", admin_base="Calgary"),
            CourtLocation(name="Edson", city="Edson", admin_base="Hinton"),
            CourtLocation(name="Evansburg", city="Evansburg", admin_base="Stony Plain"),
            CourtLocation(name="Fairview", city="Fairview", admin_base="Peace River"),
            CourtLocation(name="Falher", city="Falher", admin_base="Peace River"),
            CourtLocation(name="Fort Chipewyan", city="Fort Chipewyan", admin_base="Fort McMurray"),
            CourtLocation(name="Fort Macleod", city="Fort Macleod", admin_base="Lethbridge"),
            CourtLocation(name="Fort Saskatchewan", city="Fort Saskatchewan", admin_base="Edmonton"),
            CourtLocation(name="Fort Vermilion", city="Fort Vermilion", admin_base="High Level"),
            CourtLocation(name="Fox Creek", city="Fox Creek", admin_base="Whitecourt"),
            CourtLocation(name="Grande Cache", city="Grande Cache", admin_base="Grande Prairie"),
            CourtLocation(name="Hanna", city="Hanna", admin_base="Drumheller"),
            CourtLocation(name="Jasper", city="Jasper", admin_base="Hinton"),
            CourtLocation(name="Killam", city="Killam", admin_base="Camrose"),
            CourtLocation(name="Lac La Biche", city="Lac La Biche", admin_base="St. Paul"),
            CourtLocation(name="Leduc", city="Leduc", admin_base="Edmonton"),
            CourtLocation(name="Lloydminster", city="Lloydminster", admin_base="St. Paul"),
            CourtLocation(name="Mayerthorpe", city="Mayerthorpe", admin_base="Stony Plain"),
            CourtLocation(name="Morinville", city="Morinville", admin_base="St. Albert"),
            CourtLocation(name="Okotoks", city="Okotoks", admin_base="Calgary"),
            CourtLocation(name="Pincher Creek", city="Pincher Creek", admin_base="Lethbridge"),
            CourtLocation(name="Ponoka", city="Ponoka", admin_base="Wetaskiwin"),
            CourtLocation(name="Red Earth Creek", city="Red Earth Creek", admin_base="Slave Lake"),
            CourtLocation(name="Rimbey", city="Rimbey", admin_base="Wetaskiwin"),
            CourtLocation(name="Rocky Mountain House", city="Rocky Mountain House", admin_base="Red Deer"),
            CourtLocation(name="Sherwood Park", city="Sherwood Park", admin_base="Edmonton"),
            CourtLocation(name="Siksika Nation", city="Siksika Nation", admin_base="Strathmore"),
            CourtLocation(name="St. Albert", city="St. Albert", admin_base="Edmonton"),
            CourtLocation(name="St. Paul", city="St. Paul", admin_base="St. Paul", is_base_point=True),
            CourtLocation(name="Stony Plain", city="Stony Plain", admin_base="Edmonton"),
            CourtLocation(name="Strathmore", city="Strathmore", admin_base="Calgary"),
            CourtLocation(name="Swan Hills", city="Swan Hills", admin_base="Barrhead"),
            CourtLocation(name="Taber", city="Taber", admin_base="Lethbridge"),
            CourtLocation(name="Tofield", city="Tofield", admin_base="Camrose"),
            CourtLocation(name="Turner Valley", city="Turner Valley", admin_base="Calgary", notes="Now in Diamond Valley"),
            CourtLocation(name="Vegreville", city="Vegreville", admin_base="Tofield"),
            CourtLocation(name="Vermilion", city="Vermilion", admin_base="St. Paul"),
            CourtLocation(name="Viking", city="Viking", admin_base="Wainwright"),
            CourtLocation(name="Wabasca-Desmarais", city="Wabasca-Desmarais", admin_base="Slave Lake"),
            CourtLocation(name="Wainwright", city="Wainwright", admin_base="Vermilion"),
            CourtLocation(name="Wetaskiwin", city="Wetaskiwin", is_base_point=True),
            CourtLocation(name="Whitecourt", city="Whitecourt", admin_base="Stony Plain"),
            # ...additional small circuits exist; catalog reflects official list (~72).
        ]
        # 

        acj_hearings = [
            HearingTypeEnum.CRIM_FIRST_APPEARANCE,
            HearingTypeEnum.CRIM_DOCKET,
            HearingTypeEnum.CRIM_BAIL_HEARING,
            HearingTypeEnum.CRIM_PRELIMINARY_INQUIRY,
            HearingTypeEnum.CRIM_ARRAIGNMENT,
            HearingTypeEnum.TRIAL_CRIMINAL_JUDGE_ALONE,
            HearingTypeEnum.CRIM_SENTENCING,
            HearingTypeEnum.ACJ_CIVIL_TRIAL,
            HearingTypeEnum.FAMILY_DOCKET,
            HearingTypeEnum.FAMILY_SPECIAL_CHAMBERS,
            HearingTypeEnum.EICC_FAMILY,
        ]

        common_filings = [
            FilingTypeEnum.STATEMENT_OF_CLAIM, FilingTypeEnum.STATEMENT_OF_DEFENCE,
            FilingTypeEnum.COUNTERCLAIM, FilingTypeEnum.REPLY,
            FilingTypeEnum.ORIGINATING_APPLICATION, FilingTypeEnum.APPLICATION,
            FilingTypeEnum.AFFIDAVIT, FilingTypeEnum.AFFIDAVIT_OF_RECORDS,
            FilingTypeEnum.LIST_OF_RECORDS, FilingTypeEnum.BRIEF_OR_MEMORANDUM,
            FilingTypeEnum.CONSENT_ORDER_SUBMISSION, FilingTypeEnum.ORDER,
            FilingTypeEnum.JUDGMENT, FilingTypeEnum.TRANSCRIPT,
        ]
        abca_filings = [
            FilingTypeEnum.NOTICE_OF_APPEAL, FilingTypeEnum.APPEAL_RECORD,
            FilingTypeEnum.FACTUM, FilingTypeEnum.EXTRACTS_OF_KEY_EVIDENCE,
            FilingTypeEnum.BOOK_OF_AUTHORITIES,
        ]

        acj = Court(
            key="ALBERTA_COURT_OF_JUSTICE",
            level=CourtLevelEnum.TRIAL_PROVINCIAL,
            formal_name="Alberta Court of Justice",
            short_name="ACJ",
            divisions=[
                CourtDivisionEnum.CIVIL_CLAIMS, CourtDivisionEnum.CRIMINAL,
                CourtDivisionEnum.FAMILY, CourtDivisionEnum.YOUTH, CourtDivisionEnum.TRAFFIC
            ],
            locations=acj_locations,
            hearing_types=acj_hearings,
            filing_types=common_filings,
            order_types=[OrderTypeEnum.SCHEDULING_ENDORSEMENT, OrderTypeEnum.INTERIM_ORDER,
                         OrderTypeEnum.FINAL_ORDER, OrderTypeEnum.CONSENT_ORDER,
                         OrderTypeEnum.REASONS_FOR_JUDGMENT, OrderTypeEnum.MINUTE_ENTRY]
        )

        kb = Court(
            key="COURT_OF_KINGS_BENCH_OF_ALBERTA",
            level=CourtLevelEnum.TRIAL_SUPERIOR,
            formal_name="Court of King’s Bench of Alberta",
            short_name="KB",
            divisions=[
                CourtDivisionEnum.CIVIL, CourtDivisionEnum.FAMILY, CourtDivisionEnum.CRIMINAL,
                CourtDivisionEnum.SURROGATE, CourtDivisionEnum.COMMERCIAL_LIST, CourtDivisionEnum.APPLICATIONS
            ],
            locations=kb_locations,
            hearing_types=kb_hearings,
            filing_types=common_filings + [FilingTypeEnum.SENTENCING_SUBMISSIONS],
            order_types=[OrderTypeEnum.SCHEDULING_ENDORSEMENT, OrderTypeEnum.INTERIM_ORDER,
                         OrderTypeEnum.FINAL_ORDER, OrderTypeEnum.CONSENT_ORDER,
                         OrderTypeEnum.REASONS_FOR_JUDGMENT, OrderTypeEnum.MINUTE_ENTRY]
        )

        abca = Court(
            key="COURT_OF_APPEAL_OF_ALBERTA",
            level=CourtLevelEnum.APPEAL,
            formal_name="Court of Appeal of Alberta",
            short_name="ABCA",
            divisions=[CourtDivisionEnum.APPEALS],
            locations=[
                CourtLocation(name="Calgary (Registry)", city="Calgary", is_base_point=True,
                              notes="Appeals south of Red Deer file at Calgary."),
                CourtLocation(name="Edmonton (Registry)", city="Edmonton", is_base_point=True,
                              notes="Appeals north of Red Deer file at Edmonton."),
            ],
            hearing_types=[
                HearingTypeEnum.ABCA_APPLICATIONS_LIST,
                HearingTypeEnum.ABCA_SINGLE_JUDGE_APPLICATION,
                HearingTypeEnum.ABCA_APPEAL_HEARING
            ],
            filing_types=abca_filings,
            order_types=[OrderTypeEnum.REASONS_FOR_JUDGMENT, OrderTypeEnum.INTERIM_ORDER,
                         OrderTypeEnum.FINAL_ORDER, OrderTypeEnum.MINUTE_ENTRY]
        )
        # 

        return AlbertaCourtCatalog(acj=acj, kb=kb, abca=abca)
