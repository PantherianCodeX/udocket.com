from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

import requests

from ..audio import probe_audio_metadata


def _now_utc() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _sha256sum(fp: Path) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for ch in iter(lambda: f.read(65536), b""):
            h.update(ch)
    return h.hexdigest()


def _have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


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


def _append_jsonl(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _record_batch_location(
    case_dir: Path,
    case_id: str,
    job_id: str,
    location: str,
    region: str,
    language: str,
) -> None:
    partial = {
        "case_id": case_id,
        "azure_transcription_url": location,
        "azure_region": region,
        "language": language,
        "status": "starting",
        "timestamp_utc": _now_utc(),
    }
    ops_dir = case_dir / "ops"
    for name in (f"{case_id}_transcription_log.json", f"{job_id}_transcription_log.json"):
        path = ops_dir / name
        try:
            if path.exists():
                current = json.loads(path.read_text(encoding="utf-8"))
            else:
                current = {}
            if current.get("azure_transcription_url") and current["azure_transcription_url"] != location:
                current["previous_azure_transcription_url"] = current["azure_transcription_url"]
            current.update(partial)
            path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    try:
        _append_jsonl(
            ops_dir / "ops_transcription.jsonl",
            {
                "ts": _now_utc(),
                "case_id": case_id,
                "event": "batch_location",
                "azure_transcription_url": location,
            },
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


def _ensure_wav(input_path: Path, out_dir: Path, case_id: str) -> Path:
    if input_path.suffix.lower() == ".wav":
        return input_path
    if not _have_ffmpeg():
        raise RuntimeError("ffmpeg missing. Install ffmpeg or provide a .wav file.")
    out = input_path.with_suffix(".tmp.wav")
    import subprocess

    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-ac", "1", "-ar", "16000", str(out)]
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
    return out


def ensure_wav(input_path: Path, out_dir: Path, case_id: str) -> Path:
    """Public helper to produce a 16 kHz mono WAV for batch uploads."""
    return _ensure_wav(input_path, out_dir, case_id)


def _sdk_version() -> str:
    try:
        import pkgutil

        return pkgutil.get_loader("azure.cognitiveservices.speech").path or "unknown"
    except Exception:
        return "unknown"


def _iso8601_to_seconds(val: str) -> float:
    try:
        if not isinstance(val, str) or not val.startswith("PT"):
            return 0.0
        h = m = 0.0
        s = 0.0
        import re as _re

        mobj = _re.search(r"(\d+(?:\.\d+)?)H", val)
        if mobj:
            h = float(mobj.group(1))
        mobj = _re.search(r"(\d+(?:\.\d+)?)M", val)
        if mobj:
            m = float(mobj.group(1))
        mobj = _re.search(r"(\d+(?:\.\d+)?)S", val)
        if mobj:
            s = float(mobj.group(1))
        return h * 3600.0 + m * 60.0 + s
    except Exception:
        return 0.0


def _to_seconds(val: Any) -> float:
    try:
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            if val > 1_000_000:
                return float(val) / 10_000_000.0
            return float(val)
        if isinstance(val, str):
            if val.startswith("PT"):
                return _iso8601_to_seconds(val)
            return float(val)
    except Exception:
        return 0.0
    return 0.0


def _summarize_batch_error(payload: Any) -> str:
    try:
        if isinstance(payload, dict):
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                parts = []
                for err in errors:
                    if not isinstance(err, dict):
                        parts.append(str(err))
                        continue
                    code = err.get("code")
                    message = err.get("message") or err.get("description") or err.get("errorMessage")
                    target = err.get("target")
                    segment = " | ".join(
                        p
                        for p in (
                            f"code={code}" if code else None,
                            message,
                            f"target={target}" if target else None,
                        )
                        if p
                    )
                    parts.append(segment or str(err))
                return "; ".join(parts)
            if isinstance(errors, dict) and errors:
                code = errors.get("code")
                message = errors.get("message") or errors.get("description")
                return " | ".join(p for p in (f"code={code}" if code else None, message) if p)
            error_obj = payload.get("error")
            if isinstance(error_obj, dict):
                code = error_obj.get("code")
                message = error_obj.get("message") or error_obj.get("description")
                return " | ".join(p for p in (f"code={code}" if code else None, message) if p) or str(error_obj)
            details = payload.get("details")
            if isinstance(details, list) and details:
                return "; ".join(_summarize_batch_error(item) for item in details)
            props = payload.get("properties")
            if isinstance(props, dict) and props.get("error"):
                return _summarize_batch_error(props.get("error"))
        return str(payload)
    except Exception:
        return repr(payload)


def _rest_batch_transcribe(
    audio_url: str,
    lang: str,
    key: str,
    region: str,
    diarization: bool,
    on_location: Optional[Callable[[str], None]] = None,
) -> Tuple[str, Optional[float], Dict[str, Any]]:
    base = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.2"
    create_url = base + "/transcriptions"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "displayName": f"uDocket transcription {_now_utc()}",
        "locale": lang,
        "contentUrls": [audio_url],
        "properties": {
            "wordLevelTimestampsEnabled": True,
            "punctuationMode": "DictatedAndAutomatic",
            "profanityFilterMode": "Masked",
        },
    }
    if diarization:
        payload["properties"]["diarizationEnabled"] = True
    r = requests.post(create_url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()

    loc = r.headers.get("Location") or r.json().get("self")
    if not loc:
        raise RuntimeError("REST create did not return a polling location")

    if on_location is not None:
        try:
            on_location(loc)
        except Exception:
            pass

    t0 = time.time()
    while True:
        pr = requests.get(loc, headers=headers, timeout=30)
        pr.raise_for_status()
        pdata = pr.json()
        status = pdata.get("status")
        if status in ("Succeeded", "Failed"):
            break
        if time.time() - t0 > 5400:
            raise RuntimeError("REST batch timeout waiting for completion")
        time.sleep(5)
    if status != "Succeeded":
        err = _summarize_batch_error(pdata)
        try:
            detail = json.dumps(pdata, ensure_ascii=False)[:800]
        except Exception:
            detail = repr(pdata)
        raise RuntimeError(f"REST batch status={status}: {err} (details={detail})")

    fr = requests.get(loc + "/files", headers=headers, timeout=30)
    fr.raise_for_status()
    files_payload = fr.json()
    files = files_payload.get("values", [])
    text_url = None
    for f in files:
        if f.get("kind") == "Transcription":
            links = f.get("links") or {}
            text_url = links.get("contentUrl") or links.get("content")
            if text_url:
                break
    if not text_url:
        raise RuntimeError("REST files did not include a Transcription contentUrl")
    tresp = requests.get(text_url, timeout=60)
    tresp.raise_for_status()

    try:
        jd = tresp.json()
        meta: Dict[str, Any] = {"diarization": diarization, "azure_transcription_url": loc}
        dur_s: Optional[float] = None
        try:
            rp = jd.get("recognizedPhrases") or []
            max_end = 0.0
            seg_count = 0
            for p in rp:
                off = _to_seconds(p.get("offset") or p.get("offsetInTicks"))
                dur = _to_seconds(p.get("duration") or p.get("durationInTicks"))
                max_end = max(max_end, off + dur)
                seg_count += 1
                words = p.get("nBest", [{}])[0].get("words") or []
                for w in words:
                    woff = _to_seconds(w.get("offset") or w.get("offsetInTicks"))
                    wdur = _to_seconds(w.get("duration") or w.get("durationInTicks"))
                    max_end = max(max_end, off + woff + wdur)
            if max_end > 0:
                dur_s = max_end
            meta["segments"] = seg_count
        except Exception:
            dur_s = None

        lines: list[str] = []
        avg_conf = None
        conf_sum = 0.0
        conf_n = 0
        if diarization:
            rp = jd.get("recognizedPhrases") or []
            rp_sorted = sorted(rp, key=lambda p: _to_seconds(p.get("offset") or p.get("offsetInTicks")))
            spk_ids = set()
            for p in rp_sorted:
                nbest = p.get("nBest") or []
                best = nbest[0] if nbest else {}
                text = (best.get("display") or best.get("lexical") or "").strip()
                if not text:
                    continue
                c = best.get("confidence")
                if isinstance(c, (int, float)):
                    conf_sum += float(c)
                    conf_n += 1
                spk = p.get("speaker") or p.get("channel")
                if spk is not None:
                    spk_ids.add(spk)
                off = _to_seconds(p.get("offset") or p.get("offsetInTicks"))
                mm = int(off // 60)
                ss = int(off % 60)
                if spk is not None:
                    lines.append(f"[{mm:02d}:{ss:02d}] SPK_{spk}: {text}")
                else:
                    lines.append(f"[{mm:02d}:{ss:02d}] {text}")
            meta["num_speakers"] = len(spk_ids) if spk_ids else None
        if not lines:
            crp = jd.get("combinedRecognizedPhrases") or []
            for p in crp:
                t = (p.get("display") or p.get("lexical") or "").strip()
                if t:
                    lines.append(t)
            rp = jd.get("recognizedPhrases") or []
            if not lines and rp:
                for p in rp:
                    nb = p.get("nBest") or []
                    if nb:
                        t = (nb[0].get("display") or nb[0].get("lexical") or "").strip()
                        if t:
                            lines.append(t)
        if conf_n > 0:
            avg_conf = conf_sum / conf_n
        meta["avg_confidence"] = avg_conf
        if lines:
            return ("\n".join(lines), dur_s, meta)
        return (tresp.text, dur_s, meta)
    except Exception:
        return (tresp.text, None, {"diarization": diarization, "azure_transcription_url": loc})


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
            import azure.cognitiveservices.speech as speechsdk  # type: ignore
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
        self.recognizer = speechsdk.SpeechRecognizer(
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

    def _on_recognizing(self, evt) -> None:  # noqa: D401 - quiet
        return None

    def _on_recognized(self, evt) -> None:
        if evt.result.reason == self._speechsdk.ResultReason.RecognizedSpeech and evt.result.text.strip():
            self.chunks.append(evt.result.text)

    def _on_cancelled(self, evt) -> None:
        self.cancelled_reason = str(evt.reason)
        try:
            self.cancelled_details = getattr(evt, "error_details", None)
        except Exception:
            self.cancelled_details = None
        self.done.set()

    def _on_stopped(self, evt) -> None:
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
        audio_meta: Dict[str, Any] = {}
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
            try:
                audio_meta = probe_audio_metadata(audio_in)
            except Exception:
                audio_meta = {}
            if audio_in.suffix.lower() != ".wav":
                wav = _ensure_wav(audio_in, case_dir, case_id)
                converted = True
            else:
                wav = audio_in
            if _is_audio_empty(wav):
                _append_jsonl(
                    audit_jsonl,
                    {
                        "ts": _now_utc(),
                        "case_id": case_id,
                        "event": "invalid_audio",
                        "reason": "empty_or_too_short",
                        "file": audio_in.name,
                        "size": (wav.stat().st_size if wav.exists() else 0),
                    },
                )
                raise RuntimeError("Audio file appears empty or too short to transcribe.")

        # Duration & limit
        dur = None
        if not is_url:
            assert audio_in is not None
            dur = _get_duration_seconds(wav or audio_in) or _get_duration_seconds(audio_in)
            if not dur and audio_meta.get("audio_duration_s"):
                try:
                    dur = float(audio_meta.get("audio_duration_s"))
                except Exception:
                    pass
            if dur and dur / 60.0 > cfg.max_minutes:
                raise RuntimeError(
                    f"Audio too long ({int(dur)//60:02d}:{int(dur)%60:02d}) > MAX_MINUTES={cfg.max_minutes}"
                )

        # Transcribe
        attempts = 0
        text_raw: Optional[str] = None
        last_error: Optional[str] = None
        rest_meta: Dict[str, Any] = {}
        for attempt in range(cfg.retry_max):
            attempts = attempt + 1
            try:
                if mode == "batch":
                    if not is_url:
                        raise RuntimeError("Batch mode requires HTTPS URL input (use worker upload)")
                    text_raw, remote_dur, rest_meta = _rest_batch_transcribe(
                        str(input),
                        lang,
                        cfg.azure_speech_key,
                        cfg.azure_speech_region,
                        diarization,
                        on_location=lambda loc: _record_batch_location(
                            case_dir,
                            case_id,
                            str(job_id) if job_id else case_id,
                            loc,
                            cfg.azure_speech_region,
                            lang,
                        ),
                    )
                    if remote_dur and not dur:
                        dur = remote_dur
                else:
                    assert wav is not None or audio_in is not None
                    source = wav or audio_in  # prefer converted wav
                    tr = _OnDemandTranscriber(
                        audio=source, lang=lang, key=cfg.azure_speech_key, region=cfg.azure_speech_region, case_dir=case_dir, case_id=case_id, debug=cfg.debug
                    )
                    text_raw = tr.run(cfg.sdk_timeout_s)
            except Exception as e:
                _append_jsonl(
                    audit_jsonl,
                    {"ts": _now_utc(), "case_id": case_id, "event": "sdk_exception", "error": str(e), "attempt": attempts},
                )
                last_error = str(e)
                text_raw = None
            if text_raw:
                break
            if mode == "batch":
                break
            time.sleep(cfg.retry_base_s * (2**attempt))

        if not text_raw:
            msg = last_error or "No speech recognized or SDK timeout."
            meta_fail = {
                "case_id": case_id,
                "audio_file": audio_name,
                "audio_sha256": audio_sha,
                "azure_region": cfg.azure_speech_region,
                "language": lang,
                "attempts_used": attempts,
                "status": "failed",
                "error_message": msg,
                "timestamp_utc": _now_utc(),
            }
            if audio_meta:
                for key, value in audio_meta.items():
                    if value is not None and meta_fail.get(key) is None:
                        meta_fail[key] = value
            import json

            for pth in (log_json, log_json_job):
                try:
                    pth.write_text(json.dumps(meta_fail, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass
            _append_jsonl(audit_jsonl, {"ts": _now_utc(), "case_id": case_id, "event": "failed", "exit": 2, **meta_fail})
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
        import json

        meta = {
            "case_id": case_id,
            "audio_file": audio_name,
            "audio_sha256": audio_sha,
            "transcript_file": transcript_out.name,
            "transcript_sha256": _sha256sum(transcript_out),
            "azure_region": cfg.azure_speech_region,
            "language": lang,
            "audio_duration_s": dur,
            "word_count": len(text_raw.split()),
            "attempts_used": attempts,
            "sdk_path": _sdk_version(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "converted_temp_wav": converted,
            "timestamp_utc": _now_utc(),
            "diarization_enabled": bool(diarization),
            "status": "succeeded",
        }
        if audio_meta:
            for key, value in audio_meta.items():
                if value is None:
                    continue
                if meta.get(key) is None:
                    meta[key] = value
        if rest_meta:
            meta.update(rest_meta)
        try:
            log_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            log_json_job.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        _append_jsonl(
            audit_jsonl,
            {"ts": _now_utc(), "case_id": case_id, "event": "transcribed", "exit": 0, **meta},
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
