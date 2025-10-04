from __future__ import annotations

import os
import shutil
from pathlib import Path
import pytest
import os

# E2E tests are expensive; skip entire module unless explicitly enabled
pytestmark = pytest.mark.e2e_transcribe
if os.getenv("E2E_TRANSCRIBE") != "1":  # pragma: no cover - opt-in
    pytest.skip("Set E2E_TRANSCRIBE=1 to run e2e transcription tests", allow_module_level=True)

RUN_ONDEMAND = os.getenv("E2E_TRANSCRIBE_ONDEMAND") == "1"


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _ensure_ffmpeg() -> None:
    if not (_have("ffmpeg") and _have("ffprobe")):
        pytest.skip("ffmpeg/ffprobe required for audio probing/conversion")


def _require_azure() -> None:
    # Gate on env flag so these don't run in normal suite
    if os.getenv("E2E_TRANSCRIBE") != "1":
        pytest.skip("Set E2E_TRANSCRIBE=1 to run end-to-end Azure tests")
    key = os.getenv("AZURE_SPEECH_KEY") or os.getenv("SPEECH_KEY")
    if not (key and key.strip()):
        pytest.skip("AZURE_SPEECH_KEY missing; cannot run Azure STT e2e test")
    region = (os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION") or "canadacentral").strip().lower()
    if region not in {"canadacentral", "canadaeast"}:
        pytest.skip("Azure region must be canadacentral/canadaeast for e2e tests")


def _require_on_demand_sdk() -> None:
    if not RUN_ONDEMAND:
        pytest.skip("Set E2E_TRANSCRIBE_ONDEMAND=1 to exercise on-demand Azure SDK e2e")
    try:
        __import__("azure.cognitiveservices.speech")
    except Exception:
        pytest.skip("azure-cognitiveservices-speech is not installed; skipping on-demand SDK e2e")


def _fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "audio"


def _make_test_variants() -> dict[str, Path]:
    root = _fixtures_dir()
    return {
        "wav_ok": root / "speech_en_hello_16k_mono.wav",
        "mp3_bad": root / "speech_en_hello_48k_stereo.mp3",
        "m4a_bad": root / "speech_en_hello_44k1_stereo.m4a",
        "ogg_bad": root / "speech_en_hello_48k_mono.ogg",
        "flac_bad": root / "speech_en_hello_16k_mono.flac",
        "wav_bad": root / "speech_en_hello_48k_stereo.wav",
    }


def _dialogue_variants() -> dict[str, Path]:
    root = _fixtures_dir()
    return {
        "wav_ok": root / "dialogue_en_two_speakers_16k_mono.wav",
        "m4a_bad": root / "dialogue_en_two_speakers_44k1_stereo.m4a",
        "mp3_bad": root / "dialogue_en_two_speakers_48k_stereo.mp3",
    }


def _copy_to_tmp(src: Path, tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dst = tmp_dir / src.name
    shutil.copy2(src, dst)
    return dst


@pytest.mark.django_db
def test_audio_normalization_exercises_conversion(tmp_path):
    _ensure_ffmpeg()
    variants = _make_test_variants()

    from packages.udocket_core.agents import normalize_audio

    # Already target format should not convert
    ok_local = _copy_to_tmp(variants["wav_ok"], tmp_path)
    res_ok = normalize_audio(ok_local, tmp_path, case_id="CASE-E2E")
    assert res_ok.converted is False
    assert res_ok.reasons == []

    # Non-wav formats should be converted (format reason)
    for key in ("mp3_bad", "m4a_bad", "ogg_bad", "flac_bad"):
        local = _copy_to_tmp(variants[key], tmp_path)
        res = normalize_audio(local, tmp_path, case_id="CASE-E2E")
        assert res.converted is True
        assert "format" in set(res.reasons)

    # Wav with wrong sample rate/channels should be converted for those reasons
    wav_local = _copy_to_tmp(variants["wav_bad"], tmp_path)
    res_wav_bad = normalize_audio(wav_local, tmp_path, case_id="CASE-E2E")
    assert res_wav_bad.converted is True
    reasons = set(res_wav_bad.reasons)
    assert {"sample_rate", "channels"}.issubset(reasons)


@pytest.mark.django_db
def test_transcription_agent_on_demand_e2e(tmp_path):
    _require_azure()
    _require_on_demand_sdk()
    _ensure_ffmpeg()
    variants = _make_test_variants()

    # Build a case_dir under tmp for isolation
    case_dir = tmp_path / "storage" / "media" / "cases" / "CASE-E2E"
    case_dir.mkdir(parents=True, exist_ok=True)

    from packages.udocket_core.agents import TranscriptionAgent, TranscriptionConfig

    cfg = TranscriptionConfig.from_env()
    agent = TranscriptionAgent(cfg)

    # 1) Convert-from-mp3 path
    out1 = agent.transcribe(
        input=str(variants["mp3_bad"]),
        case_id="CASE-E2E",
        case_dir=case_dir,
        job_id="JOB-MP3",
        language="en-CA",
        mode="on-demand",
        diarization=False,
    )
    assert out1.status == "ok"
    assert Path(out1.transcript_file).exists()
    meta1 = Path(out1.meta_json).read_text(encoding="utf-8")
    assert "\"status\": \"succeeded\"" in meta1
    assert "converted_temp_wav\": true" in meta1

    # 2) Already-ok wav path
    out2 = agent.transcribe(
        input=str(variants["wav_ok"]),
        case_id="CASE-E2E",
        case_dir=case_dir,
        job_id="JOB-WAV",
        language="en-CA",
        mode="on-demand",
        diarization=False,
    )
    assert out2.status == "ok"
    assert Path(out2.transcript_file).exists()
    meta2 = Path(out2.meta_json).read_text(encoding="utf-8")
    assert "\"status\": \"succeeded\"" in meta2
    assert "converted_temp_wav\": false" in meta2


@pytest.mark.django_db
def test_transcribe_task_on_demand_e2e(tmp_path, settings):
    _require_azure()
    _require_on_demand_sdk()
    _ensure_ffmpeg()
    variants = _make_test_variants()

    # Configure storage root under tmp
    settings.PLATFORM_DEV_OPEN = True
    settings.STORAGE_ROOT = str(tmp_path / "storage")
    settings.MEDIA_ROOT = str(tmp_path / "media")

    from apps.platform.accounts.models import Organization
    from apps.platform.cases.models import Case
    from apps.platform.jobs.models import Job
    from apps.platform.operations import tasks as op_tasks

    org = Organization.objects.create(name="E2E Org")
    case = Case.objects.create(id="CASE-E2E-TASK", title="E2E Transcribe Task", organization=org)

    # Place mp3 under the case's audio folder to mirror typical layout
    case_audio_dir = Path(settings.STORAGE_ROOT) / "media" / "cases" / str(case.id) / "audio"
    case_audio_dir.mkdir(parents=True, exist_ok=True)
    src_mp3 = variants["mp3_bad"]
    audio_path = case_audio_dir / f"{str('JOB-TASK')}__sample.mp3"
    shutil.copy2(src_mp3, audio_path)

    job = Job.objects.create(case=case, organization=org, audio_input=str(audio_path), mode=Job.Mode.ON_DEMAND, diarization=False, language="en-CA")

    result = op_tasks.transcribe_job.run(case_id=str(case.id), job_id=str(job.id), audio_input=str(audio_path), mode=Job.Mode.ON_DEMAND, diarization=False)
    assert result["status"] == "SUCCEEDED"

    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED
    assert job.transcript_path
    assert Path(job.transcript_path).exists()


@pytest.mark.django_db
def test_transcribe_task_batch_diarization_e2e(tmp_path, settings):
    _require_azure()
    # Blob requirements for batch mode
    try:
        __import__("azure.storage.blob")
    except Exception:
        pytest.skip("azure-storage-blob not installed; skipping batch e2e")
    from django.conf import settings as dj
    if not (
        getattr(dj, "AZURE_BLOB_CONTAINER", None)
        and (getattr(dj, "AZURE_BLOB_CONNECTION_STRING", None) or (
            getattr(dj, "AZURE_BLOB_ACCOUNT", None) and getattr(dj, "AZURE_BLOB_KEY", None)
        ))
    ):
        pytest.skip("AZURE_BLOB_* not configured; skipping batch e2e")

    settings.PLATFORM_DEV_OPEN = True
    settings.STORAGE_ROOT = str(tmp_path / "storage")
    settings.MEDIA_ROOT = str(tmp_path / "media")

    from apps.platform.accounts.models import Organization
    from apps.platform.cases.models import Case
    from apps.platform.jobs.models import Job
    from apps.platform.operations import tasks as op_tasks

    org = Organization.objects.create(name="E2E Org Batch")
    case = Case.objects.create(id="CASE-E2E-BATCH", title="E2E Batch Diarization", organization=org)

    variants = _dialogue_variants()
    src_wav = variants["wav_ok"]
    case_audio_dir = Path(settings.STORAGE_ROOT) / "media" / "cases" / str(case.id) / "audio"
    case_audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = case_audio_dir / f"{'JOB-BATCH-DIAR'}__dialogue.wav"
    shutil.copy2(src_wav, audio_path)

    job = Job.objects.create(case=case, organization=org, audio_input=str(audio_path), mode=Job.Mode.BATCH, diarization=True, language="en-CA")
    result = op_tasks.transcribe_job.run(case_id=str(case.id), job_id=str(job.id), audio_input=str(audio_path), mode=Job.Mode.BATCH, diarization=True)
    assert result["status"] == "SUCCEEDED"
    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED
    assert job.transcript_path and Path(job.transcript_path).exists()
    # Transcript should include diarization speaker tags
    ttext = Path(job.transcript_path).read_text(encoding="utf-8", errors="ignore")
    assert "SPK_" in ttext


@pytest.mark.django_db
def test_transcribe_task_batch_convert_and_diarize_e2e(tmp_path, settings):
    _require_azure()
    try:
        __import__("azure.storage.blob")
    except Exception:
        pytest.skip("azure-storage-blob not installed; skipping batch e2e")
    from django.conf import settings as dj
    if not (
        getattr(dj, "AZURE_BLOB_CONTAINER", None)
        and (getattr(dj, "AZURE_BLOB_CONNECTION_STRING", None) or (
            getattr(dj, "AZURE_BLOB_ACCOUNT", None) and getattr(dj, "AZURE_BLOB_KEY", None)
        ))
    ):
        pytest.skip("AZURE_BLOB_* not configured; skipping batch e2e")

    settings.PLATFORM_DEV_OPEN = True
    settings.STORAGE_ROOT = str(tmp_path / "storage")
    settings.MEDIA_ROOT = str(tmp_path / "media")

    from apps.platform.accounts.models import Organization
    from apps.platform.cases.models import Case
    from apps.platform.jobs.models import Job
    from apps.platform.operations import tasks as op_tasks
    from apps.platform.operations.storage import ops_dir

    org = Organization.objects.create(name="E2E Org Batch 2")
    case = Case.objects.create(id="CASE-E2E-BATCH2", title="E2E Batch Convert+Diarize", organization=org)

    variants = _dialogue_variants()
    src_bad = variants["m4a_bad"]
    case_audio_dir = Path(settings.STORAGE_ROOT) / "media" / "cases" / str(case.id) / "audio"
    case_audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = case_audio_dir / f"{'JOB-BATCH-CONV'}__dialogue.m4a"
    shutil.copy2(src_bad, audio_path)

    job = Job.objects.create(case=case, organization=org, audio_input=str(audio_path), mode=Job.Mode.BATCH, diarization=True, language="en-CA")
    result = op_tasks.transcribe_job.run(case_id=str(case.id), job_id=str(job.id), audio_input=str(audio_path), mode=Job.Mode.BATCH, diarization=True, force_wav_conversion=False)
    assert result["status"] == "SUCCEEDED"
    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED
    assert job.transcript_path and Path(job.transcript_path).exists()
    # Per-job ops meta should record conversion details and diarization
    meta_path = ops_dir(str(case.id), job.organization_id) / f"{job.id}_transcription_log.json"
    if meta_path.exists():
        payload = meta_path.read_text(encoding="utf-8", errors="ignore")
        assert "converted_audio_file" in payload or "batch_upload_converted\": true" in payload
        assert "\"diarization_enabled\": true" in payload
