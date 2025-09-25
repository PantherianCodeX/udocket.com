from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.operations.models import LLMProviderSetting


@pytest.mark.django_db
def test_case_llm_settings_updates_summary_defaults(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(id="org-llm", name="LLM Org")
    case = Case.objects.create(id="case-llm", title="LLM Case", organization=org)
    user = User.objects.create_user(username="llm-user", password="pw")
    CaseMembership.objects.create(case=case, user=user, role=CaseMembership.Role.OWNER)

    client = Client()
    client.force_login(user)

    payload = {
        "target": "summary",
        "overrides": {
            "summarize.context_builder": {
                "provider": "local",
                "model": "offline_v1",
                "fallbacks": [],
                "allow_offline_fallback": True,
            },
            "summarize.extract_outline": {
                "provider": "azure",
                "model": "gpt-4o-mini",
                "fallbacks": ["local", "azure"],
                "allow_offline_fallback": False,
            },
        },
        "provider_chain": ["azure", "local", "azure"],
    }

    resp = client.post(
        f"/cases/{case.id}/llm/settings/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    overrides = data["overrides"]
    assert overrides["summarize.context_builder"]["provider"] == "local"
    assert overrides["summarize.extract_outline"]["fallbacks"] == ["local", "azure"]
    # provider_chain should be deduplicated and lower-cased
    assert data["provider_chain"] == ["azure", "local"]

    stored = {
        setting.stage_key: setting
        for setting in LLMProviderSetting.objects.filter(organization=org)
    }
    assert "summarize.context_builder" in stored
    assert stored["summarize.context_builder"].provider == "local"
    assert stored["summarize.context_builder"].fallbacks == []
    assert stored["summarize.context_builder"].allow_local_fallback is True

    assert "summarize.extract_outline" in stored
    assert stored["summarize.extract_outline"].provider == "azure"
    assert stored["summarize.extract_outline"].model == "gpt-4o-mini"
    assert stored["summarize.extract_outline"].fallbacks == ["local", "azure"]

