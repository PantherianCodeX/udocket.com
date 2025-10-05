# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from _typeshed import Incomplete
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import cached_property as cached_property
from mozilla_django_oidc.auth import OIDCAuthenticationBackend as OIDCAuthenticationBackend
from mozilla_django_oidc.utils import absolutify as absolutify, add_state_and_verifier_and_nonce_to_session as add_state_and_verifier_and_nonce_to_session, generate_code_challenge as generate_code_challenge, import_from_settings as import_from_settings

LOGGER: Incomplete

class SessionRefresh(MiddlewareMixin):
    """Refreshes the session with the OIDC RP after expiry seconds

    For users authenticated with the OIDC RP, verify tokens are still valid and
    if not, force the user to re-authenticate silently.

    """
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
    def exempt_urls(self):
        '''Generate and return a set of url paths to exempt from SessionRefresh

        This takes the value of ``settings.OIDC_EXEMPT_URLS`` and appends three
        urls that mozilla-django-oidc uses. These values can be view names or
        absolute url paths.

        :returns: list of url paths (for example "/oidc/callback/")

        '''
    @cached_property
    def exempt_url_patterns(self):
        '''Generate and return a set of url patterns to exempt from SessionRefresh

        This takes the value of ``settings.OIDC_EXEMPT_URLS`` and returns the
        values that are compiled regular expression patterns.

        :returns: list of url patterns (for example,
            ``re.compile(r"/user/[0-9]+/image")``)
        '''
    def is_refreshable_url(self, request):
        """Takes a request and returns whether it triggers a refresh examination

        :arg HttpRequest request:

        :returns: boolean

        """
    def process_request(self, request): ...
