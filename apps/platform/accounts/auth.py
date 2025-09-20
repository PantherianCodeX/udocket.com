from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


User = get_user_model()


class KeycloakOIDCBackend(OIDCAuthenticationBackend):
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
        user.save()
        return user


class OIDCMappingCallback:
    """Optional callback hook if additional mapping is needed later."""

    def __call__(self, *args, **kwargs) -> None:  # pragma: no cover - placeholder
        return None

