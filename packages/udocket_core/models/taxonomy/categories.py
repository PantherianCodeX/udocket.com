from __future__ import annotations
from enum import Enum

class CountryCode(str, Enum):
    CA = "CA"
    US = "US"
    OTHER = "OTHER"

class CourtLevel(str, Enum):
    FIRST_INSTANCE_GENERAL  = "FIRST_INSTANCE_GENERAL"
    FIRST_INSTANCE_SUPERIOR = "FIRST_INSTANCE_SUPERIOR"
    INTERMEDIATE_APPEAL     = "INTERMEDIATE_APPEAL"
    COURT_OF_LAST_RESORT    = "COURT_OF_LAST_RESORT"
    SPECIALIZED             = "SPECIALIZED"
    UNKNOWN_LEVEL           = "UNKNOWN_LEVEL"

class Division(str, Enum):
    CIVIL        = "CIVIL"
    FAMILY       = "FAMILY"
    CRIMINAL     = "CRIMINAL"
    YOUTH        = "YOUTH"
    TRAFFIC      = "TRAFFIC"
    PROBATE      = "PROBATE"
    APPLICATIONS = "APPLICATIONS"
    APPEALS      = "APPEALS"
    COMMERCIAL   = "COMMERCIAL"
    UNKNOWN      = "UNKNOWN"

class HearingCategory(str, Enum):
    # Civil / Family (trial)
    CIV_MOTIONS_REGULAR       = "CIV_MOTIONS_REGULAR"
    CIV_MOTIONS_SPECIAL       = "CIV_MOTIONS_SPECIAL"
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
