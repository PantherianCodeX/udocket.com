# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from _typeshed import Incomplete

LOGGER: Incomplete

def parse_www_authenticate_header(header):
    """
    Convert a WWW-Authentication header into a dict that can be used
    in a JSON response.
    """
def import_from_settings(attr, *args):
    """
    Load an attribute from the django settings.

    :raises:
        ImproperlyConfigured
    """
def absolutify(request, path):
    """Return the absolute URL of a path."""
def is_authenticated(user):
    """return True if the user is authenticated.
    This is necessary because in Django 1.10 the `user.is_authenticated`
    stopped being a method and is now a property.
    Actually `user.is_authenticated()` actually works, thanks to a backwards
    compat trick in Django. But in Django 2.0 it will cease to work
    as a callable method.
    """
def base64_url_encode(bytes_like_obj):
    """Return a URL-Safe, base64 encoded version of bytes_like_obj

    Implements base64urlencode as described in
    https://datatracker.ietf.org/doc/html/rfc7636#appendix-A
    """
def base64_url_decode(string_like_obj):
    """Return the bytes encoded in a URL-Safe, base64 encoded string.
    Implements inverse of base64urlencode as described in
    https://datatracker.ietf.org/doc/html/rfc7636#appendix-A
    This function is not used by the OpenID client; it's just for testing PKCE related functions.
    """
def generate_code_challenge(code_verifier, method):
    """Return a code_challege, which proves knowledge of the code_verifier.
    The code challenge is generated according to method which must be one
    of the methods defined in https://datatracker.ietf.org/doc/html/rfc7636#section-4.2:
    - plain:
    code_challenge = code_verifier
    - S256:
    code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
    """
def add_state_and_verifier_and_nonce_to_session(request, state, params, code_verifier=None) -> None:
    """
    Stores the `state` and `nonce` parameters and an optional `code_verifier` (for PKCE) in a
    session dictionary which maps `state` -> {nonce, code_verifier}.  Each entry includes
    the time when it was added. The dictionary can contain multiple state -> {nonce, code_verifier}
    mappings to allow parallel logins with multiple browser sessions.
    To keep the session space to a reasonable size, the dictionary is kept at 50
    state -> {nonce, code_verifier} mappings maximum.
    """
