# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

class FFIError(Exception):
    __module__: str

class CDefError(Exception):
    __module__: str

class VerificationError(Exception):
    __module__: str

class VerificationMissing(Exception):
    __module__: str

class PkgConfigError(Exception):
    __module__: str
