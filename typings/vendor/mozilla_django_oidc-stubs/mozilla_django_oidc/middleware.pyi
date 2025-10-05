# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from _typeshed import Incomplete
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import cached_property as cached_property
from mozilla_django_oidc.auth import OIDCAuthenticationBackend as OIDCAuthenticationBackend
from mozilla_django_oidc.utils import absolutify as absolutify, add_state_and_verifier_and_nonce_to_session as add_state_and_verifier_and_nonce_to_session, generate_code_challenge as generate_code_challenge, import_from_settings as import_from_settings

LOGGER: Incomplete

class SessionRefresh(MiddlewareMixin):
    OIDC_EXEMPT_URLS: Incomplete
    OIDC_OP_AUTHORIZATION_ENDPOINT: Incomplete
    OIDC_RP_CLIENT_ID: Incomplete
    OIDC_STATE_SIZE: Incomplete
    OIDC_AUTHENTICATION_CALLBACK_URL: Incomplete
    OIDC_RP_SCOPES: Incomplete
    OIDC_USE_NONCE: Incomplete
    OIDC_NONCE_SIZE: Incomplete
    def __init__(self, get_response) -> None: ...
    @staticmethod
    def get_settings(attr, *args): ...
    @cached_property
    def exempt_urls(self): ...
    @cached_property
    def exempt_url_patterns(self): ...
    def is_refreshable_url(self, request): ...
    def process_request(self, request): ...
