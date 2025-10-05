# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from _typeshed import Incomplete
from mozilla_django_oidc.auth import OIDCAuthenticationBackend as OIDCAuthenticationBackend
from mozilla_django_oidc.utils import import_from_settings as import_from_settings, parse_www_authenticate_header as parse_www_authenticate_header
from rest_framework import authentication

LOGGER: Incomplete

def get_oidc_backend():
    """
    Get the Django auth backend that uses OIDC.
    """

class OIDCAuthentication(authentication.BaseAuthentication):
    """
    Provide OpenID authentication for DRF.
    """
    www_authenticate_realm: str
    backend: Incomplete
    def __init__(self, backend=None) -> None: ...
    def authenticate(self, request):
        """
        Authenticate the request and return a tuple of (user, token) or None
        if there was no authentication attempt.
        """
    def get_access_token(self, request):
        """
        Get the access token based on a request.

        Returns None if no authentication details were provided. Raises
        AuthenticationFailed if the token is incorrect.
        """
    def authenticate_header(self, request):
        """
        If this method returns None, a generic HTTP 403 forbidden response is
        returned by DRF when authentication fails.

        By making the method return a string, a 401 is returned instead. The
        return value will be used as the WWW-Authenticate header.
        """
