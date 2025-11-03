from __future__ import annotations

# pyright: strict

import hashlib
import logging
import os
import platform
import re
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..audio import probe_audio_metadata
from packages.udocket_common.json_utils import (
    JSONObject,
    coerce_json_object,
    coerce_json_value,
    merge_json_objects,
    read_json_object,
    write_json_object,
)
from packages.udocket_common.time import format_utc
from .common import append_jsonl
from .common.azure_speech import AzureSpeechClient, AzureSpeechClientConfig, AzureSpeechError

TARGET_SAMPLE_RATE_HZ = 16000
TARGET_AUDIO_CODEC = "pcm_s16le"
TARGET_AUDIO_CHANNELS = 1  # Future multi-channel diarization may raise this
TARGET_SAMPLE_FMT = "s16"
TARGET_BITS_PER_SAMPLE = 16
TARGET_AUDIO_MIME = "audio/wav"
TARGET_SAMPLE_FMTS = {"s16", "s16p", "s16le"}


logger = logging.getLogger("udocket.transcribe.agent")


def _json_payload(**items: object) -> JSONObject:
    return {key: coerce_json_value(value) for key, value in items.items()}


@dataclass
class AudioNormalizationResult:
    path: Path
    converted: bool
    metadata: JSONObject
    reasons: list[str]
    original_metadata: JSONObject | None = None


def _now_utc() -> str:
    return format_utc(timespec="seconds")


def _sha256sum(fp: Path) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for ch in iter(lambda: f.read(65536), b""):
            h.update(ch)
    return h.hexdigest()


def _have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _analyze_audio_conversion(
    input_path: Path,
    metadata: JSONObject | None = None,
    *,
    diarization: bool = False,
) -> tuple[list[str], JSONObject]:
    meta: JSONObject = dict(metadata) if metadata else {}
    if not meta:
        try:
            meta = coerce_json_object(probe_audio_metadata(input_path))
        except Exception:
            meta = {}

    reasons: list[str] = []

    suffix = input_path.suffix.lower()
    if suffix != ".wav":
        reasons.append("format")

    codec_value = meta.get("audio_codec")
    codec = codec_value.lower() if isinstance(codec_value, str) else ""
    if codec and codec != TARGET_AUDIO_CODEC:
        reasons.append("codec")

    sample_fmt_val = meta.get("audio_sample_fmt")
    sample_fmt = sample_fmt_val.lower() if isinstance(sample_fmt_val, str) else ""
    if sample_fmt and sample_fmt not in TARGET_SAMPLE_FMTS:
        reasons.append("sample_format")

    bits = meta.get("audio_bits_per_sample")
    if isinstance(bits, (int, float)) and int(bits) != TARGET_BITS_PER_SAMPLE:
        reasons.append("bit_depth")

    sample_rate = meta.get("audio_sample_rate_hz")
    if isinstance(sample_rate, (int, float)) and int(sample_rate) != TARGET_SAMPLE_RATE_HZ:
        reasons.append("sample_rate")

    channels = meta.get("audio_channels")
    if isinstance(channels, (int, float)):
        target_channels = TARGET_AUDIO_CHANNELS
        # Multi-channel diarization is future work; stay mono for now.
        if int(channels) != target_channels:
            reasons.append("channels")

    return reasons, meta


def normalize_audio(
    input_path: Path,
    out_dir: Path,
    case_id: str,
    *,
    metadata: JSONObject | None = None,
    diarization: bool = False,
    force: bool = False,
) -> AudioNormalizationResult:
    reasons, meta = _analyze_audio_conversion(input_path, metadata=metadata, diarization=diarization)
    if force and "forced" not in reasons:
        reasons.append("forced")
    should_convert = bool(reasons) or force
    if not should_convert:
        original_meta = dict(meta)
        return AudioNormalizationResult(
            path=input_path,
            converted=False,
            metadata=dict(meta),
            reasons=[],
            original_metadata=original_meta,
        )
    if not _have_ffmpeg():
        raise RuntimeError("ffmpeg missing. Install ffmpeg to normalize audio inputs.")

    out = input_path.with_suffix(".tmp.wav")
    import subprocess

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-ac",
        str(TARGET_AUDIO_CHANNELS),
        "-ar",
        str(TARGET_SAMPLE_RATE_HZ),
        "-c:a",
        TARGET_AUDIO_CODEC,
        "-sample_fmt",
        TARGET_SAMPLE_FMT,
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        errp = out_dir / "ops" / f"{case_id}_ffmpeg_error.log"
        errp.parent.mkdir(parents=True, exist_ok=True)
        errp.write_text(
            "CMD: "
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + proc.stdout
            + "\n\nSTDERR:\n"
            + proc.stderr
            + "\n",
            encoding="utf-8",
        )
        raise RuntimeError("ffmpeg conversion failed; see ops ffmpeg_error.log")

    # Update metadata to reflect target format
    original_meta = dict(meta)

    meta.update(
        _json_payload(
            audio_codec=TARGET_AUDIO_CODEC,
            audio_sample_rate_hz=TARGET_SAMPLE_RATE_HZ,
            audio_channels=TARGET_AUDIO_CHANNELS,
            audio_sample_fmt=TARGET_SAMPLE_FMT,
            audio_bits_per_sample=TARGET_BITS_PER_SAMPLE,
            audio_mime=TARGET_AUDIO_MIME,
            audio_conversion_reasons=reasons,
        )
    )

    return AudioNormalizationResult(
        path=out,
        converted=True,
        metadata=dict(meta),
        reasons=reasons,
        original_metadata=original_meta,
    )


def _get_duration_seconds(p: Path) -> Optional[float]:
    if not shutil.which("ffprobe"):
        return None
    try:
        import subprocess

        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(p),
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return float(out)
    except Exception:
        return None


def _is_audio_empty(p: Path) -> bool:
    try:
        size = p.stat().st_size
    except Exception:
        size = 0
    if size <= 512:
        return True
    dur = _get_duration_seconds(p)
    return dur is not None and dur <= 0.1


def _insert_timestamps(text: str, interval: int) -> str:
    if not text or interval <= 0:
        return text
    words = text.split()
    words_per_sec = 2.5
    chunk = max(1, int(interval * words_per_sec))
    parts: list[str] = []
    t = 0
    for i in range(0, len(words), chunk):
        parts.append(f"[~{t//60:02d}:{t%60:02d}] " + " ".join(words[i : i + chunk]))
        t += interval
    return "\n".join(parts)


def _record_batch_location(
    case_dir: Path,
    case_id: str,
    job_id: str,
    location: str,
    region: str,
    language: str,
) -> None:
    partial = _json_payload(
        case_id=case_id,
        azure_transcription_url=location,
        azure_region=region,
        language=language,
        status="starting",
        timestamp_utc=_now_utc(),
    )
    ops_dir = case_dir / "ops"
    for name in (f"{case_id}_transcription_log.json", f"{job_id}_transcription_log.json"):
        path = ops_dir / name
        try:
            current = read_json_object(path)
            existing_location = current.get("azure_transcription_url")
            if isinstance(existing_location, str) and existing_location and existing_location != location:
                current["previous_azure_transcription_url"] = existing_location
            current.update(partial)
            write_json_object(path, current)
        except Exception:
            pass
    try:
        append_jsonl(
            ops_dir / "ops_transcription.jsonl",
            _json_payload(
                ts=_now_utc(),
                case_id=case_id,
                event="batch_location",
                azure_transcription_url=location,
            ),
        )
    except Exception:
        pass


def _next_versioned(path: Path) -> Path:
    if not path.exists():
        return path
    m = re.match(r"(.+)_v(\d+)$", path.stem)
    if m:
        root, ver = m.groups()
        ver = int(ver)
    else:
        root, ver = path.stem, 1
    while True:
        ver += 1
        cand = path.with_name(f"{root}_v{ver}{path.suffix}")
        if not cand.exists():
            return cand


def _ensure_wav(
    input_path: Path,
    out_dir: Path,
    case_id: str,
    *,
    metadata: JSONObject | None = None,
    diarization: bool = False,
    force: bool = False,
) -> Path:
    result = normalize_audio(
        input_path,
        out_dir,
        case_id,
        metadata=metadata,
        diarization=diarization,
        force=force,
    )
    return result.path


def ensure_wav(input_path: Path, out_dir: Path, case_id: str) -> Path:
    """Public helper to produce a 16 kHz mono WAV for batch uploads."""
    return _ensure_wav(input_path, out_dir, case_id)


def _sdk_version() -> str:
    try:
        import azure.cognitiveservices.speech as speechsdk

        version = getattr(speechsdk, "__version__", None)
        if isinstance(version, str) and version:
            return version
    except Exception:
        return "unknown"
    return "unknown"


@dataclass
class TranscriptionConfig:
    azure_speech_key: str
    azure_speech_region: str = "canadacentral"  # canadacentral|canadaeast only
    language: str = "en-CA"
    timestamp_sec: int = 180
    max_minutes: int = 120
    sdk_timeout_s: int = 5400
    retry_max: int = 3
    retry_base_s: int = 3
    debug: bool = False

    @classmethod
    def from_env(cls) -> "TranscriptionConfig":
        key = (os.getenv("AZURE_SPEECH_KEY") or os.getenv("SPEECH_KEY") or "").strip()
        if not key:
            raise RuntimeError("Missing AZURE_SPEECH_KEY (or SPEECH_KEY)")
        region = (os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION") or "canadacentral").strip().lower()
        return cls(
            azure_speech_key=key,
            azure_speech_region=region,
            language=os.getenv("LANGUAGE", "en-CA").strip(),
            timestamp_sec=int(os.getenv("TIMESTAMP_SEC", "180")),
            max_minutes=int(os.getenv("MAX_MINUTES", "120")),
            sdk_timeout_s=int(os.getenv("SDK_TIMEOUT_S", "5400")),
            retry_max=int(os.getenv("RETRY_MAX", "3")),
            retry_base_s=int(os.getenv("RETRY_BASE_S", "3")),
            debug=(os.getenv("DEBUG", "0").strip() == "1"),
        )


@dataclass
class TranscriptionResult:
    status: str
    transcript_file: Path
    region: str
    language: str
    attempts: int
    duration_s: Optional[float]
    meta_json: Path
    meta_log: Path
    audit_jsonl: Path


class _OnDemandTranscriber:
    def __init__(self, audio: Path, lang: str, key: str, region: str, case_dir: Path, case_id: str, debug: bool) -> None:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except Exception as e:  # pragma: no cover - import-time
            raise RuntimeError("Azure Speech SDK not installed (pip install azure-cognitiveservices-speech)") from e

        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_recognition_language = lang

        if debug:
            try:
                sdk_log = case_dir / "ops" / f"{case_id}_speechsdk.log"
                speech_config.set_property(speechsdk.PropertyId.Speech_LogFilename, str(sdk_log))
            except Exception:
                pass

        try:
            speech_config.request_word_level_timestamps()
        except Exception:
            pass
        try:
            speech_config.set_profanity(speechsdk.ProfanityOption.Masked)
        except Exception:
            pass

        self._speechsdk = speechsdk
        self.recognizer: speechsdk.SpeechRecognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=speechsdk.audio.AudioConfig(filename=str(audio)),
        )
        self.chunks: list[str] = []
        self.done = threading.Event()
        self.cancelled_reason: Optional[str] = None
        self.cancelled_details: Optional[str] = None

        self.recognizer.recognizing.connect(self._on_recognizing)
        self.recognizer.recognized.connect(self._on_recognized)
        self.recognizer.cancelled.connect(self._on_cancelled)
        self.recognizer.session_stopped.connect(self._on_stopped)

    def _on_recognizing(self, evt: object) -> None:  # noqa: D401 - quiet
        return None

    def _on_recognized(self, evt: object) -> None:
        result = getattr(evt, "result", None)
        reason = getattr(result, "reason", None)
        text = getattr(result, "text", "")
        if reason == self._speechsdk.ResultReason.RecognizedSpeech and isinstance(text, str) and text.strip():
            self.chunks.append(text)

    def _on_cancelled(self, evt: object) -> None:
        self.cancelled_reason = str(getattr(evt, "reason", ""))
        try:
            self.cancelled_details = getattr(evt, "error_details", None)
        except Exception:
            self.cancelled_details = None
        self.done.set()

    def _on_stopped(self, evt: object) -> None:
        self.done.set()

    def run(self, timeout: int) -> Optional[str]:
        self.recognizer.start_continuous_recognition()
        try:
            finished = self.done.wait(timeout)
            if not finished:
                return None
            return "\n".join(self.chunks).strip()
        finally:
            try:
                self.recognizer.stop_continuous_recognition()
            except Exception:
                pass


class TranscriptionAgent:
    """Library API for uDocket transcription agent.

    Mirrors the CLI behavior while being importable from Django/Celery.
    """

    ALLOWED_REGIONS = {"canadacentral", "canadaeast"}
    AUDIO_EXTS = {".m4a", ".wav", ".mp3", ".flac", ".ogg", ".aac"}

    def __init__(self, config: Optional[TranscriptionConfig] = None) -> None:
        self.config = config or TranscriptionConfig.from_env()
        if self.config.azure_speech_region not in self.ALLOWED_REGIONS:
            raise RuntimeError("Region must be canadacentral or canadaeast")
        self._speech_client: AzureSpeechClient | None = None

    def _get_speech_client(self) -> AzureSpeechClient:
        if self._speech_client is None:
            cfg = self.config
            client_cfg = AzureSpeechClientConfig(
                key=cfg.azure_speech_key,
                region=cfg.azure_speech_region,
                request_timeout_s=float(cfg.retry_base_s * 6),
                poll_interval_s=float(max(1, cfg.retry_base_s)),
                poll_timeout_s=float(cfg.sdk_timeout_s),
            )
            self._speech_client = AzureSpeechClient(client_cfg, logger=logger)
        return self._speech_client

    def transcribe(
        self,
        *,
        input: str | Path,
        case_id: str,
        case_dir: Path,
        job_id: Optional[str] = None,
        language: Optional[str] = None,
        mode: str = "on-demand",
        diarization: bool = False,
        diagnostics: bool = False,
    ) -> TranscriptionResult:
        cfg = self.config
        speech_client = self._get_speech_client()
        try:
            speech_client.ensure_health(force=False)
        except AzureSpeechError as exc:
            raise RuntimeError(f"Azure Speech health check failed: {exc}") from exc
        lang = (language or cfg.language).strip()
        case_dir = Path(case_dir).resolve()
        (case_dir / "transcript").mkdir(parents=True, exist_ok=True)
        (case_dir / "ops").mkdir(parents=True, exist_ok=True)

        # Determine input source and job id
        is_url = False
        audio_in: Optional[Path] = None
        audio_name: str
        if isinstance(input, Path):
            audio_in = input.expanduser().resolve()
            audio_name = audio_in.name
        else:
            s = str(input)
            if s.startswith("http://") or s.startswith("https://"):
                is_url = True
                from urllib.parse import urlparse, unquote

                try:
                    audio_name = unquote(urlparse(s).path.split("/")[-1]) or "audio"
                except Exception:
                    audio_name = "audio"
            else:
                audio_in = Path(s).expanduser().resolve()
                audio_name = audio_in.name

        if not job_id:
            m = re.match(r"([^_]+)__", audio_name)
            job_id = m.group(1) if m else case_id

        transcript_out = (case_dir / "transcript" / f"{job_id}__transcript.txt").resolve()
        log_txt = case_dir / "ops" / f"{case_id}_transcription.log"
        log_json = case_dir / "ops" / f"{case_id}_transcription_log.json"
        audit_jsonl = case_dir / "ops" / "ops_transcription.jsonl"
        log_txt_job = case_dir / "ops" / f"{job_id}_transcription.log"
        log_json_job = case_dir / "ops" / f"{job_id}_transcription_log.json"

        # Start logs
        for pth, line in (
            (log_txt, f"{_now_utc()} START | file={audio_name} mode={mode} diar={bool(diarization)} lang={lang} region={cfg.azure_speech_region}\n"),
            (log_txt_job, f"{_now_utc()} START | file={audio_name} mode={mode} diar={bool(diarization)} lang={lang} region={cfg.azure_speech_region}\n"),
        ):
            try:
                pth.write_text(line, encoding="utf-8")
            except Exception:
                pass

        # Validate / prepare audio
        audio_sha = None
        wav: Optional[Path] = None
        converted = False
        audio_meta: JSONObject = {}
        conversion_reasons: list[str] = []
        if not is_url:
            assert audio_in is not None
            if audio_in.suffix.lower() not in self.AUDIO_EXTS:
                raise RuntimeError(f"Unsupported audio extension: {audio_in.suffix}")
            audio_sha = _sha256sum(audio_in)
            try:
                with open(log_txt_job, "a", encoding="utf-8") as f:
                    f.write(f"{_now_utc()} INFO | local_sha256 {audio_sha}\n")
            except Exception:
                pass

            normalization = normalize_audio(
                audio_in,
                case_dir,
                case_id,
                metadata=None,
                diarization=bool(diarization),
            )
            wav = normalization.path if normalization.converted else audio_in
            converted = normalization.converted
            audio_meta = normalization.metadata
            conversion_reasons = normalization.reasons

            if converted:
                append_jsonl(
                    audit_jsonl,
                    _json_payload(
                        ts=_now_utc(),
                        case_id=case_id,
                        event="audio_normalized",
                        reasons=conversion_reasons,
                        source_file=audio_in.name,
                    ),
                )

            if _is_audio_empty(wav):
                append_jsonl(
                    audit_jsonl,
                    _json_payload(
                        ts=_now_utc(),
                        case_id=case_id,
                        event="invalid_audio",
                        reason="empty_or_too_short",
                        file=audio_in.name,
                        size=wav.stat().st_size if wav.exists() else 0,
                    ),
                )
                raise RuntimeError("Audio file appears empty or too short to transcribe.")

        # Duration & limit
        dur = None
        if not is_url:
            assert audio_in is not None
            dur = _get_duration_seconds(wav or audio_in) or _get_duration_seconds(audio_in)
            if not dur:
                duration_value = audio_meta.get("audio_duration_s")
                if isinstance(duration_value, (int, float, str)):
                    try:
                        dur = float(duration_value)
                    except Exception:
                        dur = None
            if dur and dur / 60.0 > cfg.max_minutes:
                raise RuntimeError(
                    f"Audio too long ({int(dur)//60:02d}:{int(dur)%60:02d}) > MAX_MINUTES={cfg.max_minutes}"
                )

        # Transcribe
        attempts = 0
        text_raw: Optional[str] = None
        last_error: Optional[str] = None
        rest_meta: JSONObject = {}
        for attempt in range(cfg.retry_max):
            attempts = attempt + 1
            try:
                if mode == "batch":
                    if not is_url:
                        raise RuntimeError("Batch mode requires HTTPS URL input (use worker upload)")
                    batch_result = speech_client.run_batch_transcription(
                        audio_url=str(input),
                        locale=lang,
                        diarization=diarization,
                        display_name=f"uDocket transcription {_now_utc()}",
                        on_location=lambda loc: _record_batch_location(
                            case_dir,
                            case_id,
                            str(job_id) if job_id else case_id,
                            loc,
                            cfg.azure_speech_region,
                            lang,
                        ),
                    )
                    text_raw = batch_result.text
                    rest_meta = batch_result.metadata
                    if batch_result.duration_s and not dur:
                        dur = batch_result.duration_s
                else:
                    assert wav is not None or audio_in is not None
                    source = wav if wav is not None else audio_in
                    if source is None:
                        raise RuntimeError("Missing audio path for transcription")
                    tr = _OnDemandTranscriber(
                        audio=source,
                        lang=lang,
                        key=cfg.azure_speech_key,
                        region=cfg.azure_speech_region,
                        case_dir=case_dir,
                        case_id=case_id,
                        debug=cfg.debug,
                    )
                    text_raw = tr.run(cfg.sdk_timeout_s)
            except AzureSpeechError as exc:
                speech_client.ensure_health(force=True)
                append_jsonl(
                    audit_jsonl,
                    _json_payload(
                        ts=_now_utc(),
                        case_id=case_id,
                        event="sdk_exception",
                        error=str(exc),
                        attempt=attempts,
                    ),
                )
                last_error = str(exc)
                text_raw = None
            except Exception as exc:
                append_jsonl(
                    audit_jsonl,
                    _json_payload(
                        ts=_now_utc(),
                        case_id=case_id,
                        event="sdk_exception",
                        error=str(exc),
                        attempt=attempts,
                    ),
                )
                last_error = str(exc)
                text_raw = None
            if text_raw:
                break
            if mode == "batch":
                break
            time.sleep(cfg.retry_base_s * (2**attempt))

        if not text_raw:
            msg = last_error or "No speech recognized or SDK timeout."
            meta_fail = _json_payload(
                case_id=case_id,
                audio_file=audio_name,
                audio_sha256=audio_sha,
                azure_region=cfg.azure_speech_region,
                language=lang,
                attempts_used=attempts,
                status="failed",
                error_message=msg,
                timestamp_utc=_now_utc(),
            )
            if audio_meta:
                for key, value in audio_meta.items():
                    if value is not None and meta_fail.get(key) is None:
                        meta_fail[key] = value
            for pth in (log_json, log_json_job):
                try:
                    write_json_object(pth, meta_fail)
                except Exception:
                    pass
            append_jsonl(
                audit_jsonl,
                merge_json_objects(
                    meta_fail,
                    _json_payload(ts=_now_utc(), case_id=case_id, event="failed", exit=2),
                ),
            )
            raise RuntimeError(msg)

        # Build transcript output
        interval = 0 if diarization else cfg.timestamp_sec
        text_ts = _insert_timestamps(text_raw, interval)
        transcript_out = _next_versioned(transcript_out)

        def _human_dur(sec: Optional[float]) -> str:
            if not sec:
                return "unknown"
            m, s = int(sec // 60), int(sec % 60)
            return f"{m:02d}:{s:02d}"

        header = "\n".join(
            [
                "DRAFT — LEGAL INFORMATION ONLY — CLIENT REVIEW REQUIRED",
                f"Case: {case_id}",
                f"Audio: {audio_name}",
                f"SHA256: {audio_sha or 'n/a (remote)'}",
                f"Region: {cfg.azure_speech_region}",
                f"Language: {lang}",
                f"Duration: {_human_dur(dur)}",
                f"Transcribed: {_now_utc()}",
                "-" * 72,
            ]
        )
        transcript_out.parent.mkdir(parents=True, exist_ok=True)
        transcript_out.write_text(header + "\n" + text_ts + "\n", encoding="utf-8")

        # Meta

        python_version = platform.python_version()
        platform_label = platform.platform()

        sdk_version_value = _sdk_version()

        meta = _json_payload(
            case_id=case_id,
            audio_file=audio_name,
            audio_sha256=audio_sha,
            transcript_file=transcript_out.name,
            transcript_sha256=_sha256sum(transcript_out),
            azure_region=cfg.azure_speech_region,
            language=lang,
            audio_duration_s=dur,
            word_count=len(text_raw.split()),
            attempts_used=attempts,
            sdk_path=sdk_version_value,
            python=python_version,
            platform=platform_label,
            converted_temp_wav=converted,
            timestamp_utc=_now_utc(),
            diarization_enabled=bool(diarization),
            status="succeeded",
        )
        if audio_meta:
            for key, value in audio_meta.items():
                if value is None:
                    continue
                if meta.get(key) is None:
                    meta[key] = value
        if rest_meta:
            meta = merge_json_objects(meta, rest_meta)
        try:
            write_json_object(log_json, meta)
            write_json_object(log_json_job, meta)
        except Exception:
            pass
        append_jsonl(
            audit_jsonl,
            merge_json_objects(
                meta,
                _json_payload(ts=_now_utc(), case_id=case_id, event="transcribed", exit=0),
            ),
        )
        try:
            with open(log_txt, "a", encoding="utf-8") as f:
                f.write(
                    f"{_now_utc()} DONE | out={transcript_out.name} words={meta.get('word_count')} dur_s={dur} diar={bool(diarization)}\n"
                )
            with open(log_txt_job, "a", encoding="utf-8") as f:
                f.write(
                    f"{_now_utc()} DONE | out={transcript_out.name} words={meta.get('word_count')} dur_s={dur} diar={bool(diarization)}\n"
                )
        except Exception:
            pass

        return TranscriptionResult(
            status="ok",
            transcript_file=transcript_out,
            region=cfg.azure_speech_region,
            language=lang,
            attempts=attempts,
            duration_s=dur,
            meta_json=log_json_job,
            meta_log=log_txt_job,
            audit_jsonl=audit_jsonl,
        )
