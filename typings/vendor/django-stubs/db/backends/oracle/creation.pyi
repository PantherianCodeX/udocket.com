# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from typing import Any

from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.backends.oracle.base import DatabaseWrapper

TEST_DATABASE_PREFIX: str

class DatabaseCreation(BaseDatabaseCreation):
    connection: DatabaseWrapper
    def set_as_test_mirror(self, primary_settings_dict: Any) -> None: ...
    def test_db_signature(self) -> Any: ...
