from __future__ import annotations

from typing import Any, Optional

import logging

from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.conf import settings

import jwt
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions

from apps.platform.cases.models import CaseMembership, Case


log = logging.getLogger("apps.platform.accounts.auth")


User = get_user_model()


class KeycloakOIDCBackend(OIDCAuthenticationBackend):
    def filter_users_by_claims(self, claims):  # type: ignore[override]
        """Find existing users by Keycloak subject first, then email/username.

        This prevents duplicate local users when usernames are derived from `sub`.
        """
        sub = (claims.get("sub") or "").strip() or None
        email = (claims.get("email") or "").strip() or None
        preferred = (claims.get("preferred_username") or "").strip() or None
        qs = User.objects.none()
        if sub:
            qs = User.objects.filter(kc_sub=sub) | User.objects.filter(username=sub)
        elif email:
            qs = User.objects.filter(email__iexact=email) | User.objects.filter(username__iexact=email)
        elif preferred:
            qs = User.objects.filter(username__iexact=preferred)
        return qs.distinct()

    def get_username(self, claims):  # type: ignore[override]
        email = (claims.get("email") or "").strip()
        preferred = (claims.get("preferred_username") or "").strip()
        if email:
            return email
        if preferred:
            return preferred
        sub = claims.get("sub")
        if sub:
            return sub
        return super().get_username(claims)

    def verify_claims(self, claims):  # type: ignore[override]
        issuer = claims.get("iss")
        expected = getattr(settings, "OIDC_ISSUER", None)
        if expected and issuer and issuer.rstrip("/") != expected.rstrip("/"):
            log.warning("OIDC issuer mismatch: expected %s, got %s", expected, issuer)
            return False
        if "sub" not in claims:
            log.warning("OIDC claims missing subject")
            return False
        scopes = (self.get_settings("OIDC_RP_SCOPES", "openid email profile") or "")
        if "email" in scopes.split() and not claims.get("email"):
            log.warning("OIDC claims missing email; proceeding with subject %s", claims.get("sub"))
        return True

    def create_user(self, claims: dict[str, Any]) -> Any:  # type: ignore[override]
        user = super().create_user(claims)
        return self.update_user(user, claims)

    def update_user(self, user: Any, claims: dict[str, Any]) -> Any:  # type: ignore[override]
        # Map Keycloak standard claims
        sub = claims.get("sub")
        email = claims.get("email")
        name = claims.get("name") or f"{claims.get('given_name','')} {claims.get('family_name','')}".strip()
        if hasattr(user, "kc_sub"):
            setattr(user, "kc_sub", sub)
        if email and not getattr(user, "email", None):
            user.email = email
        if name and hasattr(user, "display_name"):
            user.display_name = name
        # Optional staff mapping: mark staff if user is in admin group
        is_staff = getattr(user, "is_staff", False)
        try:
            groups = claims.get("groups") or []
            if any(g in ("/udocket-admin", "udocket-admin", "admin") for g in groups):
                is_staff = True
        except Exception:
            pass
        user.is_staff = is_staff
        user.save()
        # Optional: sync memberships from group claims (format: case:<CASE_ID>:<ROLE>)
        if getattr(settings, "OIDC_SYNC_MEMBERSHIPS", False):
            groups = claims.get("groups") or []
            prefix = getattr(settings, "OIDC_CASE_GROUP_PREFIX", "case:")
            sep = getattr(settings, "OIDC_CASE_GROUP_SEPARATOR", ":")
            for g in groups:
                if not isinstance(g, str) or not g.startswith(prefix):
                    continue
                try:
                    rest = g[len(prefix):]
                    parts = rest.split(sep)
                    case_id = parts[0]
                    role = (parts[1] if len(parts) > 1 else getattr(settings, "OIDC_CASE_DEFAULT_ROLE", "REVIEWER")).upper()
                    # Only sync if case exists
                    try:
                        c = Case.objects.filter(pk=case_id).first()
                    except Exception:
                        c = None
                    if not c:
                        continue
                    cm, _ = CaseMembership.objects.get_or_create(case=c, user=user, defaults={"role": role})
                    if cm.role != role:
                        cm.role = role
                        cm.save(update_fields=["role"])
                except Exception:
                    continue
        return user


class OIDCMappingCallback:
    """Optional callback hook if additional mapping is needed later."""

    def __call__(self, *args, **kwargs) -> None:  # pragma: no cover - placeholder
        return None


class KeycloakJWTAuthentication(BaseAuthentication):
    """DRF auth class that validates Keycloak JWTs via remote JWKS.

    On success, returns a local User (creating/updating minimally) using claims.
    Falls through gracefully if no Bearer token.
    """

    def authenticate(self, request):  # type: ignore[override]
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b"bearer":
            return None
        if len(auth) == 1:
            raise exceptions.AuthenticationFailed("Invalid Authorization header.")
        try:
            raw_token = auth[1].decode("utf-8")
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid Authorization header encoding.")

        jwks_url = getattr(settings, "OIDC_JWKS_URL", None) or settings.SIMPLE_JWT.get("JWK_URL")  # type: ignore[attr-defined]
        issuer = getattr(settings, "OIDC_ISSUER", None)
        audience = getattr(settings, "OIDC_AUDIENCE", None)
        if not jwks_url:
            # JWT not configured; treat as no auth provided
            return None

        try:
            signing_key = jwt.PyJWKClient(jwks_url).get_signing_key_from_jwt(raw_token).key
            claims = jwt.decode(
                raw_token,
                signing_key,
                algorithms=["RS256"],
                audience=audience,
                issuer=issuer,
                options={"verify_aud": bool(audience), "verify_signature": True, "verify_iss": bool(issuer)},
            )
        except Exception as e:
            raise exceptions.AuthenticationFailed(f"Invalid token: {e}")

        sub = claims.get("sub")
        if not sub:
            raise exceptions.AuthenticationFailed("Missing subject in token")

        email = claims.get("email")
        username = email or sub
        user, created = User.objects.get_or_create(kc_sub=sub, defaults={"username": username, "email": email or ""})
        # Minimal updates
        changed = False
        if email and user.email != email:
            user.email = email
            changed = True
        name = claims.get("name") or f"{claims.get('given_name','')} {claims.get('family_name','')}".strip()
        if name and getattr(user, "display_name", None) != name and hasattr(user, "display_name"):
            user.display_name = name
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if changed:
            try:
                user.save()
            except Exception:
                pass

        # Optionally sync memberships from group claims
        if getattr(settings, "OIDC_SYNC_MEMBERSHIPS", False):
            try:
                KeycloakOIDCBackend().update_user(user, claims)
            except Exception:
                pass
        return (user, None)
