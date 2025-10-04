import uuid as _uuid

import pytest
from django.test import TestCase

from apps.platform.accounts.models import Organization
from apps.platform.operations.llm import (
    get_org_provider_credentials,
    upsert_org_provider_credential,
    upsert_org_provider_credential_by_uuid,
    delete_org_provider_credential_by_uuid,
)


class ProviderCredentialUUIDTests(TestCase):
    def setUp(self) -> None:
        self.org = Organization.objects.create(name="Test Org")

    def test_uuid_roundtrip_create_update_delete(self):
        # Create via standard upsert (no uuid provided)
        upsert_org_provider_credential(
            organization_id=str(self.org.id),
            provider="custom",
            display_name="Custom Provider",
            endpoint="https://example.invalid",
            api_key="secret",
            models=[{"name": "m1", "enabled": True}],
            metadata={"headers": {"X-Test": "1"}},
            enabled=True,
        )

        creds = get_org_provider_credentials(str(self.org.id))
        assert "custom" in creds
        uid = creds["custom"].get("uid")
        assert uid and len(str(uid)) > 0

        # Update via UUID path
        upsert_org_provider_credential_by_uuid(
            organization_id=str(self.org.id),
            provider_uid=uid,
            provider="custom",
            display_name="Custom Provider 2",
            endpoint="https://example2.invalid",
            api_key=None,  # preserve key
            models=[{"name": "m1", "enabled": False}],
            metadata={"headers": {"X-Test": "2"}},
            enabled=False,
        )

        creds2 = get_org_provider_credentials(str(self.org.id))
        assert creds2["custom"]["display_name"] == "Custom Provider 2"
        assert creds2["custom"]["is_enabled"] is False

        # Delete via UUID
        delete_org_provider_credential_by_uuid(str(self.org.id), uid)
        creds3 = get_org_provider_credentials(str(self.org.id))
        assert "custom" not in creds3

