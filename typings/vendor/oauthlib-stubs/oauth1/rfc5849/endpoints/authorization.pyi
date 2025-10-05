# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from .base import BaseEndpoint as BaseEndpoint

class AuthorizationEndpoint(BaseEndpoint):
    def create_verifier(self, request, credentials): ...
    def create_authorization_response(
        self, uri, http_method: str = "GET", body=None, headers=None, realms=None, credentials=None
    ): ...
    def get_realms_and_credentials(self, uri, http_method: str = "GET", body=None, headers=None): ...
