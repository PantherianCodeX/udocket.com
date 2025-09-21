from __future__ import annotations

from django.core.management import call_command, CommandError
from django.test import TestCase

from apps.platform.authorization.models import PermissionPreset, PresetFieldPolicy
from apps.platform.artifacts.registry import artifact_field_keys


class SyncArtifactFieldsCommandTests(TestCase):
    def setUp(self) -> None:
        self.preset = PermissionPreset.objects.create(name="Test Preset")

    def test_check_detects_missing(self) -> None:
        with self.assertRaises(CommandError):
            call_command("sync_artifact_fields", "--check")

    def test_apply_creates_missing_entries(self) -> None:
        call_command("sync_artifact_fields")
        expected = artifact_field_keys()
        actual = set(
            PresetFieldPolicy.objects.filter(preset=self.preset, resource="ARTIFACT")
            .values_list("type", "field_name")
        )
        self.assertEqual(expected, actual)
        for policy in PresetFieldPolicy.objects.filter(preset=self.preset):
            self.assertIsInstance(policy.actions, list)

    def test_delete_stale(self) -> None:
        # Seed command so required entries exist
        call_command("sync_artifact_fields")
        PresetFieldPolicy.objects.bulk_create(
            [
                PresetFieldPolicy(
                    preset=self.preset,
                    resource="ARTIFACT",
                    type="UNKNOWN",
                    field_name="foo",
                    actions=["view"],
                )
            ]
        )
        call_command("sync_artifact_fields", "--delete-stale")
        self.assertFalse(
            PresetFieldPolicy.objects.filter(preset=self.preset, type="UNKNOWN", field_name="foo").exists()
        )

    def test_no_apply_leaves_missing(self) -> None:
        PresetFieldPolicy.objects.all().delete()
        call_command("sync_artifact_fields", "--no-apply")
        expected = artifact_field_keys()
        remaining = set(
            PresetFieldPolicy.objects.filter(preset=self.preset, resource="ARTIFACT")
            .values_list("type", "field_name")
        )
        self.assertEqual(set(), remaining)
