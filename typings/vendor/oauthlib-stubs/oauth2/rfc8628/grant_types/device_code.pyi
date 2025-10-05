# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from oauthlib.common import Request
from oauthlib.oauth2.rfc6749.grant_types.base import GrantTypeBase
from oauthlib.oauth2.rfc6749.tokens import TokenBase

class DeviceCodeGrant(GrantTypeBase):
    def create_authorization_response(self, request: Request, token_handler: TokenBase) -> tuple[dict[str, str], str, int]: ...
    def validate_token_request(self, request: Request) -> None: ...
    def create_token_response(self, request: Request, token_handler: TokenBase) -> tuple[dict[str, str], str, int]: ...
