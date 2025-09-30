from __future__ import annotations

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.operations.llm import upsert_org_provider_credential
from apps.platform.operations.tasks import _hydrate_summarize_config_from_org_credentials
from packages.udocket_core.agents.summarize_lib import SummarizeConfig


@pytest.mark.django_db
def test_hydrate_summarize_config_uses_org_credentials():
    org = Organization.objects.create(id="org-cred", name="Org Cred")

    upsert_org_provider_credential(
        organization_id=org.id,
        provider="azure",
        display_name="Azure",
        endpoint="https://example.openai.azure.com",
        api_key="secret-key",
        models=[{"name": "gpt-5-mini", "label": "gpt-5-mini-deploy"}],
        metadata={"azure_deployment": "gpt-5-mini-deploy"},
    )

    base_config = SummarizeConfig(
        azure_openai_endpoint="",
        azure_openai_key="",
        azure_openai_deployment="placeholder",
        provider_chain=["azure"],
    )

    hydrated = _hydrate_summarize_config_from_org_credentials(
        config=base_config,
        organization_id=org.id,
        provider_chain=["azure"],
        stage_map={"summarize.extract_outline": {"provider": "azure"}},
    )

    assert hydrated.azure_enabled is True
    assert hydrated.azure_openai_endpoint == "https://example.openai.azure.com"
    assert hydrated.azure_openai_key == "secret-key"
    assert hydrated.azure_openai_deployment == "gpt-5-mini-deploy"
