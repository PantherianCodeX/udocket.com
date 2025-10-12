from __future__ import annotations

import pytest

from apps.platform.accounts.auth import KeycloakOIDCBackend
from apps.platform.accounts.models import User
from tests._typing import DatabaseFixture, SettingsFixture


@pytest.mark.django_db
def test_get_username_prefers_email(db: DatabaseFixture, settings: SettingsFixture):
    # minimal endpoints so backend can initialize
    settings.OIDC_OP_TOKEN_ENDPOINT = "http://test/token"
    settings.OIDC_OP_AUTHORIZATION_ENDPOINT = "http://test/auth"
    settings.OIDC_OP_USER_ENDPOINT = "http://test/userinfo"
    settings.OIDC_OP_JWKS_ENDPOINT = "http://test/jwks"
    b = KeycloakOIDCBackend()
    claims = {"email": "alice@example.com", "preferred_username": "alice", "sub": "SUB123"}
    assert b.get_username(claims) == "alice@example.com"


@pytest.mark.django_db
def test_filter_users_by_claims_matches_kc_sub(db: DatabaseFixture, settings: SettingsFixture):
    settings.OIDC_OP_TOKEN_ENDPOINT = "http://test/token"
    settings.OIDC_OP_AUTHORIZATION_ENDPOINT = "http://test/auth"
    settings.OIDC_OP_USER_ENDPOINT = "http://test/userinfo"
    settings.OIDC_OP_JWKS_ENDPOINT = "http://test/jwks"
    u = User.objects.create_user("SUB123", email="")
    u.kc_sub = "SUB123"
    u.save(update_fields=["kc_sub"])
    b = KeycloakOIDCBackend()
    qs = b.filter_users_by_claims({"sub": "SUB123"})
    assert qs.first() == u