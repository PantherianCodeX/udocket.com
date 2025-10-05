# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from abc import abstractmethod

class CredentialProvider:
    @abstractmethod
    def get_credentials(self) -> tuple[str] | tuple[str, str]: ...

class UsernamePasswordCredentialProvider(CredentialProvider):
    username: str
    password: str
    def __init__(self, username: str | None = None, password: str | None = None) -> None: ...
    def get_credentials(self) -> tuple[str] | tuple[str, str]: ...
