import json
import uuid
from django.db import migrations, models
from pathlib import Path


def _storage_meta_path(storage_module, case_id: str, org_id: str | None, job_id: str) -> Path:
    return storage_module.ops_dir(case_id, org_id) / f"{job_id}_transcription_log.json"


def sync_job_metadata(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    try:
        from apps.platform.operations import storage as storage_module
    except Exception:  # pragma: no cover - storage path may be unavailable
        storage_module = None

    if storage_module is None:
        return

    fields = ["agent_type", "agent_label", "job_kind", "display_title", "source_job_id"]

    for job in Job.objects.only("id", "case_id", "organization_id"):  # type: ignore[attr-defined]
        case_id = str(job.case_id)
        org_id = getattr(job, "organization_id", None)
        meta_path = _storage_meta_path(storage_module, case_id, org_id, str(job.id))
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        updates: dict[str, object] = {}
        agent_type = meta.get("agent_type")
        if isinstance(agent_type, str) and agent_type.strip():
            updates["agent_type"] = agent_type.strip()[:64]
        agent_label = meta.get("agent_label")
        if isinstance(agent_label, str) and agent_label.strip():
            updates["agent_label"] = agent_label.strip()[:128]
        job_kind = meta.get("job_kind")
        if isinstance(job_kind, str) and job_kind.strip():
            updates["job_kind"] = job_kind.strip()[:64]
        job_title = meta.get("job_title") or meta.get("title") or meta.get("display_title")
        if isinstance(job_title, str) and job_title.strip():
            updates["display_title"] = job_title.strip()[:255]
        source_job_value = meta.get("source_job_id") or meta.get("converted_audio_job_id")
        if source_job_value:
            try:
                source_uuid = uuid.UUID(str(source_job_value))
            except (TypeError, ValueError):
                source_uuid = None
            if source_uuid:
                # Only set FK when the referenced job exists to avoid FK violations
                if Job.objects.filter(pk=source_uuid).exists():
                    updates["source_job_id"] = source_uuid
        if updates:
            Job.objects.filter(pk=job.id).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0006_jobnote"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="agent_label",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="job",
            name="agent_type",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="job",
            name="display_title",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="job",
            name="job_kind",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="job",
            name="source_job",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="child_jobs", to="jobs.job"),
        ),
        migrations.RunPython(sync_job_metadata, migrations.RunPython.noop),
    ]
