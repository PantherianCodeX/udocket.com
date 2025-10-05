# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

import datetime
import json

from yaml import Dumper, ScalarNode

class JSONEncoder(json.JSONEncoder): ...

class CustomScalar:
    @classmethod
    def represent_timedelta(cls, dumper: Dumper, data: datetime.timedelta) -> ScalarNode: ...
