# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from _typeshed import Incomplete
from django.contrib.auth.backends import ModelBackend
from mozilla_django_oidc.utils import absolutify as absolutify, import_from_settings as import_from_settings

LOGGER: Incomplete

def default_username_algo(email, claims=None):
    """Generate username for the Django user.

    :arg str/unicode email: the email address to use to generate a username
    :arg dic claims: the claims from your OIDC provider, currently unused

    :returns: str/unicode

    """

class OIDCAuthenticationBackend(ModelBackend):
    """Override Django's authentication."""
    OIDC_OP_TOKEN_ENDPOINT: Incomplete
    OIDC_OP_USER_ENDPOINT: Incomplete
    OIDC_OP_JWKS_ENDPOINT: Incomplete
    OIDC_RP_CLIENT_ID: Incomplete
    OIDC_RP_CLIENT_SECRET: Incomplete
    OIDC_RP_SIGN_ALGO: Incomplete
    OIDC_RP_IDP_SIGN_KEY: Incomplete
    UserModel: Incomplete
    def __init__(self, *args, **kwargs) -> None:
        """Initialize settings."""
    @staticmethod
    def get_settings(attr, *args): ...
    def describe_user_by_claims(self, claims): ...
    def filter_users_by_claims(self, claims):
        """Return all users matching the specified email."""
    def verify_claims(self, claims):
        """Verify the provided claims to decide if authentication should be allowed."""
    def create_user(self, claims):
        """Return object for a newly created user account."""
    def get_username(self, claims):
        """Generate username based on claims."""
    def update_user(self, user, claims):
        """Update existing user with new claims, if necessary save, and return user"""
    def retrieve_matching_jwk(self, token):
        """Get the signing key by exploring the JWKS endpoint of the OP."""
    def get_payload_data(self, token, key):
        """Helper method to get the payload of the JWT token."""
    def verify_token(self, token, **kwargs):
        """Validate the token signature."""
    def get_token(self, payload):
        """Return token object as a dictionary."""
    def raise_token_response_error(self, response) -> None:
        """Raises :class:`HTTPError`, if one occurred.
        as per: https://datatracker.ietf.org/doc/html/rfc6749#section-5.2
        """
    def get_userinfo(self, access_token, id_token, payload):
        """Return user details dictionary. The id_token and payload are not used in
        the default implementation, but may be used when overriding this method"""
    request: Incomplete
    def authenticate(self, request, **kwargs):
        """Authenticates a user based on the OIDC code flow."""
    def store_tokens(self, access_token, id_token) -> None:
        """Store OIDC tokens."""
    def get_or_create_user(self, access_token, id_token, payload):
        """Returns a User instance if 1 user is found. Creates a user if not found
        and configured to do so. Returns nothing if multiple users are matched."""
    def get_user(self, user_id):
        """Return a user based on the id."""
