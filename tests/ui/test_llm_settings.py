from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.operations.models import LLMConfiguration


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
        "configuration": {
            "name": "Primary summary",
            "provider_chain": ["azure"],
            "stage_map": {
                "summarize.context_builder": {
                    "provider": "azure",
                    "model": "gpt-4o-mini",
                    "max_tokens": 7200,
                    "options": {"temperature": 0.35},
                },
                "summarize.extract_outline": {
                    "provider": "azure",
                    "model": "gpt-4o-mini",
                },
            },
            "set_default": True,
        },
    }

    resp = client.post(
        f"/cases/{case.id}/llm/settings/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["target"] == "summary"
    assert isinstance(data.get("configurations"), list)
    assert data.get("active")

    stored_configs = list(LLMConfiguration.objects.filter(organization=org, target="summary"))
    assert len(stored_configs) == 1
    stored = stored_configs[0]
    assert stored.name == "Primary summary"
    assert stored.is_default is True
    assert stored.provider_chain == ["azure"]
    stage_map = stored.stage_map or {}
    assert stage_map["summarize.context_builder"]["provider"] == "azure"
    assert stage_map["summarize.context_builder"]["model"] == "gpt-4o-mini"
    assert stage_map["summarize.context_builder"]["max_tokens"] == 7200
    assert stage_map["summarize.context_builder"]["options"]["temperature"] == 0.35
