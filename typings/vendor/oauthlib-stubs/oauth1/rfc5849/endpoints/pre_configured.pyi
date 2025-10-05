# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from . import (
    AccessTokenEndpoint as AccessTokenEndpoint,
    AuthorizationEndpoint as AuthorizationEndpoint,
    RequestTokenEndpoint as RequestTokenEndpoint,
    ResourceEndpoint as ResourceEndpoint,
)

class WebApplicationServer(RequestTokenEndpoint, AuthorizationEndpoint, AccessTokenEndpoint, ResourceEndpoint):
    def __init__(self, request_validator) -> None: ...
