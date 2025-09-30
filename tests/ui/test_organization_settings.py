from __future__ import annotations

import pytest

from django.test import Client

from apps.platform.accounts.models import Organization, OrganizationMembership, User
from apps.platform.operations.models import LLMConfiguration, LLMProviderCredential


@pytest.mark.django_db
def test_organization_settings_renders_and_manages_providers(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(id="org-settings", name="Settings Org")
    user = User.objects.create_user(username="settings-user", password="password")
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.ADMIN)

    client = Client()
    client.force_login(user)
    session = client.session
    session["admin_active_org_id"] = org.id
    session.save()

    resp = client.get("/settings/organization/")
    assert resp.status_code == 200
    assert b"LLM providers" in resp.content

    resp = client.post(
        "/settings/organization/",
        data={
            "action": "provider-upsert",
            "provider": "azure",
            "display_name": "Azure Canada",
            "endpoint": "https://example.canadacentral.azure.com",
            "api_key": "secret",
            "models_payload": "",
            "metadata_json": "{\"azure_deployment\": \"gpt-4o\"}",
            "is_enabled": "on",
        },
        follow=True,
    )
    assert resp.status_code == 200
    credential = LLMProviderCredential.objects.filter(organization=org, provider="azure").first()
    assert credential is not None
    expected_uuid = str(credential.uid)
    assert any(f"provider={expected_uuid}" in url for url, _status in resp.redirect_chain)
    assert f"provider={expected_uuid}" in resp.request.get("QUERY_STRING", "")
    assert LLMProviderCredential.objects.filter(organization=org, provider="azure").exists()


@pytest.mark.django_db
def test_organization_settings_saves_configuration(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(id="org-config", name="Config Org")
    user = User.objects.create_user(username="config-user", password="password")
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.ADMIN)

    client = Client()
    client.force_login(user)
    session = client.session
    session["admin_active_org_id"] = org.id
    session.save()

    # Ensure provider credential exists so configuration can reference it
    client.post(
        "/settings/organization/",
        data={
            "action": "provider-upsert",
            "provider": "azure",
            "display_name": "Azure",
            "endpoint": "https://example.canadacentral.azure.com",
            "api_key": "secret",
            "metadata_json": "{\"azure_deployment\": \"gpt-4o\"}",
            "is_enabled": "on",
        },
    )

    resp = client.post(
        "/settings/organization/",
        data={
            "action": "config-save",
            "target": "summary",
            "name": "Org default summary",
            "description": "Primary summarization settings",
            "provider_chain": ["azure"],
            "set_default": "1",
            "stage__summarize__context_builder__provider": "azure",
            "stage__summarize__context_builder__model": "gpt-4o-mini",
            "stage__summarize__context_builder__max_tokens": "6000",
            "stage__summarize__context_builder__temperature": "0.35",
        },
        follow=True,
    )
    assert resp.status_code == 200
    stored = LLMConfiguration.objects.filter(organization=org, target="summary").first()
    assert stored is not None
    assert stored.is_default is True
    assert stored.name == "Org default summary"
    assert stored.stage_map["summarize.context_builder"]["provider"] == "azure"
    assert stored.stage_map["summarize.context_builder"]["model"] == "gpt-4o-mini"
    assert stored.stage_map["summarize.context_builder"]["max_tokens"] == 6000
    assert stored.stage_map["summarize.context_builder"]["options"]["temperature"] == 0.35


@pytest.mark.django_db
def test_provider_test_action_reports_status(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(id="org-test", name="Test Org")
    user = User.objects.create_user(username="tester", password="password")
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.ADMIN)

    client = Client()
    client.force_login(user)
    session = client.session
    session["admin_active_org_id"] = org.id
    session.save()

    client.post(
        "/settings/organization/",
        data={
            "action": "provider-upsert",
            "provider": "azure",
            "display_name": "Azure",
            "endpoint": "https://example.canadacentral.azure.com",
            "api_key": "secret",
            "metadata_json": "{\"azure_deployment\": \"gpt-4o\"}",
            "is_enabled": "on",
        },
    )

    resp = client.post(
        "/settings/organization/",
        data={
            "action": "provider-test",
            "provider": "azure",
        },
        follow=True,
    )
    assert resp.status_code == 200
    assert b"passed validation" in resp.content


@pytest.mark.django_db
def test_provider_enable_blocked_when_not_configured(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(id="org-block", name="Block Org")
    user = User.objects.create_user(username="block-user", password="password")
    OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.ADMIN)

    client = Client()
    client.force_login(user)
    session = client.session
    session["admin_active_org_id"] = org.id
    session.save()

    client.get("/settings/organization/")

    resp = client.post(
        "/settings/organization/",
        data={
            "action": "provider-toggle",
            "provider": "azure",
            "enabled": "1",
        },
        follow=True,
    )
    assert resp.status_code == 200
    assert b"API key is required" in resp.content
