# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from _typeshed import Incomplete
from django.views.generic import View
from mozilla_django_oidc.utils import absolutify as absolutify, add_state_and_verifier_and_nonce_to_session as add_state_and_verifier_and_nonce_to_session, generate_code_challenge as generate_code_challenge, import_from_settings as import_from_settings

class OIDCAuthenticationCallbackView(View):
    """OIDC client authentication callback HTTP endpoint"""
    http_method_names: Incomplete
    @staticmethod
    def get_settings(attr, *args): ...
    @property
    def failure_url(self): ...
    @property
    def success_url(self): ...
    def login_failure(self): ...
    def login_success(self): ...
    user: Incomplete
    def get(self, request):
        """Callback handler for OIDC authorization code flow"""

def get_next_url(request, redirect_field_name):
    """Retrieves next url from request

    Note: This verifies that the url is safe before returning it. If the url
    is not safe, this returns None.

    :arg HttpRequest request: the http request
    :arg str redirect_field_name: the name of the field holding the next url

    :returns: safe url or None

    """

class OIDCAuthenticationRequestView(View):
    """OIDC client authentication HTTP endpoint"""
    http_method_names: Incomplete
    OIDC_OP_AUTH_ENDPOINT: Incomplete
    OIDC_RP_CLIENT_ID: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...
    @staticmethod
    def get_settings(attr, *args): ...
    def get(self, request):
        """OIDC client authentication initialization HTTP endpoint"""
    def get_extra_params(self, request): ...

class OIDCLogoutView(View):
    """Logout helper view"""
    http_method_names: Incomplete
    @staticmethod
    def get_settings(attr, *args): ...
    @property
    def redirect_url(self):
        """Return the logout url defined in settings."""
    def post(self, request):
        """Log out the user."""
    def get(self, request):
        """Log out the user."""
