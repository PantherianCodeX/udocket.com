#!/usr/bin/env python3
"""
uDocket Transcription Agent v1.4.2 (Canada-only, WAV conversion, debug-friendly)

- File input path uses AudioConfig(filename=...), so we feed PCM WAV (mono, 16 kHz).
- Non-WAV inputs are converted via ffmpeg (requires ffmpeg installed) to <name>.tmp.wav.
- DEBUG=1 enables native Speech SDK logging to CASE_DIR/ops/<CASEID>_speechsdk.log.
- Prints a final one-line JSON summary to stdout on success for easy piping/monitoring.
"""
import os, sys, json, hashlib, subprocess, shlex, threading, shutil, platform, pkgutil, re, time, argparse, typing
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:
    print("python-dotenv not installed. Run: pip install python-dotenv", file=sys.stderr)
    sys.exit(10)

try:
    import azure.cognitiveservices.speech as speechsdk  # type: ignore
except Exception as e:
    print("Azure Speech SDK not installed. Run: pip install azure-cognitiveservices-speech", file=sys.stderr)
    sys.exit(10)

load_dotenv()

# Accept both AZURE_* and legacy SPEECH_* env names
SPEECH_KEY              = (os.getenv("AZURE_SPEECH_KEY") or os.getenv("SPEECH_KEY") or "").strip()
SPEECH_REGION           = (os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION") or "canadacentral").strip().lower()
TIMESTAMP_SEC           = int(os.getenv("TIMESTAMP_SEC", "180"))
MAX_MINUTES             = int(os.getenv("MAX_MINUTES", "120"))
SDK_TIMEOUT_S           = int(os.getenv("SDK_TIMEOUT_S", "5400"))
LANGUAGE                = os.getenv("LANGUAGE", "en-CA").strip()
RETRY_MAX               = int(os.getenv("RETRY_MAX", "3"))
RETRY_BASE_S            = int(os.getenv("RETRY_BASE_S", "3"))
KEEP_TEMP_WAV           = os.getenv("KEEP_TEMP_WAV", "0").strip() == "1"
DEBUG_MODE              = os.getenv("DEBUG", "0").strip() == "1"

ALLOWED_REGIONS = {"canadacentral", "canadaeast"}
AUDIO_EXTS      = {".m4a", ".wav", ".mp3", ".flac", ".ogg", ".aac"}

def now_utc() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def sha256sum(fp: Path) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for ch in iter(lambda: f.read(65536), b""):
            h.update(ch)
    return h.hexdigest()

def sdk_version() -> str:
    try:
        return pkgutil.get_loader("azure.cognitiveservices.speech").path or "unknown"
    except Exception:
        return "unknown"

def err_exit(code: int, msg: str):
    print(msg, file=sys.stderr)
    sys.exit(code)

def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def get_duration_seconds(p: Path) -> Optional[float]:
    if not shutil.which("ffprobe"):
        return None

def is_audio_empty(p: Path) -> bool:
    try:
        size = p.stat().st_size
    except Exception:
        size = 0
    # If file is extremely small, treat as empty
    if size <= 512:
        return True
    dur = get_duration_seconds(p)
    # Consider very short or zero duration as empty
    return dur is not None and dur <= 0.1
    try:
        out = subprocess.check_output(
            ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(p)],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        return float(out)
    except Exception:
        return None

def human_dur(sec: Optional[float]) -> str:
    if not sec:
        return "unknown"
    m, s = int(sec // 60), int(sec % 60)
    return f"{m:02d}:{s:02d}"

def insert_timestamps(text: str, interval: int) -> str:
    if not text or interval <= 0:
        return text
    words = text.split()
    words_per_sec = 2.5
    chunk = max(1, int(interval * words_per_sec))
    parts, t = [], 0
    for i in range(0, len(words), chunk):
        parts.append(f"[~{t//60:02d}:{t%60:02d}] " + " ".join(words[i:i+chunk]))
        t += interval
    return "\n".join(parts)

def write_text(p: Path, content: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def append_jsonl(p: Path, obj: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def next_versioned(path: Path) -> Path:
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

def ensure_wav(input_path: Path, case_dir: Path, case_id: str) -> Path:
    """Ensure PCM WAV; on failure, write ffmpeg stdout/stderr to ops log."""
    if input_path.suffix.lower() == ".wav":
        return input_path
    if not have_ffmpeg():
        err_exit(11, "ffmpeg missing. Install ffmpeg or provide a .wav file.")
    out = input_path.with_suffix(".tmp.wav")
    cmd = ["ffmpeg","-y","-i",str(input_path),"-ac","1","-ar","16000",str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        errp = case_dir / "ops" / f"{case_id}_ffmpeg_error.log"
        errp.parent.mkdir(parents=True, exist_ok=True)
        errp.write_text(
            "CMD: " + " ".join(cmd) + "\n\nSTDOUT:\n" + proc.stdout + "\n\nSTDERR:\n" + proc.stderr + "\n",
            encoding="utf-8"
        )
        err_exit(11, "ffmpeg conversion failed; see ops ffmpeg_error.log")
    return out

class Transcriber:
    def __init__(self, audio: Path, lang: str, case_dir: Path, case_id: str):
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        speech_config.speech_recognition_language = lang
        # Optional native SDK log file (DEBUG=1)
        if DEBUG_MODE:
            sdk_log = case_dir / "ops" / f"{case_id}_speechsdk.log"
            try:
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

        self.recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=speechsdk.audio.AudioConfig(filename=str(audio))
        )
        self.chunks = []
        self.done = threading.Event()
        self.canceled_reason = None
        self.canceled_details = None

        self.recognizer.recognizing.connect(self._on_recognizing)
        self.recognizer.recognized.connect(self._on_recognized)
        self.recognizer.canceled.connect(self._on_canceled)
        self.recognizer.session_stopped.connect(self._on_stopped)

    def _on_recognizing(self, evt):
        # could add verbose interim logs when DEBUG_MODE
        pass

    def _on_recognized(self, evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and evt.result.text.strip():
            self.chunks.append(evt.result.text)

    def _on_canceled(self, evt):
        self.canceled_reason = str(evt.reason)
        try:
            self.canceled_details = getattr(evt, "error_details", None)
        except Exception:
            self.canceled_details = None
        self.done.set()

    def _on_stopped(self, evt):
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

def parse_args():
    p = argparse.ArgumentParser(description="uDocket Azure Speech transcriber")
    p.add_argument("pos_case_dir", nargs="?")
    p.add_argument("pos_audio", nargs="?")
    p.add_argument("pos_case", nargs="?")
    p.add_argument("--input", dest="input")
    p.add_argument("--case", dest="case")
    p.add_argument("--case-dir", dest="case_dir")
    p.add_argument("--outdir", dest="outdir")
    p.add_argument("--language", dest="language")
    return p.parse_args()

def main():
    if not SPEECH_KEY or not SPEECH_REGION:
        err_exit(10, "Missing AZURE_SPEECH_KEY/AZURE_SPEECH_REGION (or SPEECH_KEY/REGION) in .env")
    if SPEECH_REGION not in ALLOWED_REGIONS:
        err_exit(13, f"Region {SPEECH_REGION} not allowed (must be canadacentral/canadaeast)")

    args = parse_args()
    # Prefer flag style used by worker template; fallback to positional
    if args.input:
        audio_in = Path(args.input).expanduser().resolve()
        if args.case_dir:
            case_dir = Path(args.case_dir).expanduser().resolve()
        elif args.outdir:
            case_dir = Path(args.outdir).expanduser().resolve().parent
        else:
            case_dir = audio_in.parent.parent  # heuristic: .../cases/<id>/audio/<file>
        case_id = args.case or case_dir.name
        lang = (args.language or LANGUAGE).strip()
    else:
        if not args.pos_case_dir or not args.pos_audio:
            err_exit(10, "Usage: python transcribe.py CASE_DIR audiofile [CASEID] or --input/--case/--outdir flags")
        case_dir = Path(args.pos_case_dir).expanduser().resolve()
        audio_in = Path(args.pos_audio).expanduser().resolve()
        case_id = args.pos_case if args.pos_case else (case_dir.name.split("_")[0] if "_" in case_dir.name else case_dir.name)
        lang = LANGUAGE
    if not case_id:
        err_exit(11, "CASEID not provided and could not be inferred from case directory name.")
    if not case_dir.exists() or not audio_in.exists():
        err_exit(11, "Bad path(s) provided")

    transcript_dir = case_dir / "transcript"
    ops_dir = case_dir / "ops"
    log_txt = ops_dir / f"{case_id}_transcription.log"
    log_json = ops_dir / f"{case_id}_transcription_log.json"
    audit_jsonl = ops_dir / "ops_transcription.jsonl"
    # Derive job_id from filename prefix if available: <jobid>__original.ext
    mjob = re.match(r"([^_]+)__", audio_in.name)
    job_id = mjob.group(1) if mjob else case_id
    transcript_out = transcript_dir / f"{job_id}__transcript.txt"

    write_text(log_txt, f"{now_utc()} START | file={audio_in.name}\n")
    if audio_in.suffix.lower() not in AUDIO_EXTS:
        err_exit(11, f"Unsupported audio extension: {audio_in.suffix}")

    audio_sha = sha256sum(audio_in)
    wav = None
    converted = False
    try:
        if audio_in.suffix.lower() != ".wav":
            wav = ensure_wav(audio_in, case_dir, case_id)
            converted = True
        else:
            wav = audio_in

        # Quick validation for empty/silent files
        if is_audio_empty(wav):
            append_jsonl(audit_jsonl, {
                "ts": now_utc(), "case_id": case_id, "event": "invalid_audio", "reason": "empty_or_too_short",
                "file": audio_in.name, "size": (wav.stat().st_size if wav.exists() else 0)
            })
            err_exit(2, "Audio file appears empty or too short to transcribe.")

        dur = get_duration_seconds(wav) or get_duration_seconds(audio_in)
        if dur and dur / 60.0 > MAX_MINUTES:
            err_exit(13, f"Audio too long ({human_dur(dur)}) > MAX_MINUTES={MAX_MINUTES}")

        attempts = 0
        text_raw = None
        for attempt in range(RETRY_MAX):
            attempts = attempt + 1
            try:
                tr = Transcriber(wav, lang, case_dir, case_id)
                text_raw = tr.run(SDK_TIMEOUT_S)
            except Exception as e:
                append_jsonl(audit_jsonl, {
                    "ts": now_utc(), "case_id": case_id, "event": "sdk_exception", "error": str(e), "attempt": attempts
                })
                text_raw = None
            if text_raw:
                break
            # record why it failed (timeout or canceled)
            if tr.canceled_reason:
                append_jsonl(audit_jsonl, {
                    "ts": now_utc(), "case_id": case_id, "event": "canceled_retry",
                    "reason": tr.canceled_reason, "details": tr.canceled_details, "attempt": attempts
                })
            else:
                append_jsonl(audit_jsonl, {
                    "ts": now_utc(), "case_id": case_id, "event": "timeout_or_empty_retry", "attempt": attempts
                })
            if attempt < RETRY_MAX - 1:
                time.sleep(RETRY_BASE_S * (2 ** attempt))

        if not text_raw:
            err_exit(2, "No speech recognized (or SDK timeout). Check audio quality and try again.")

        text_ts = insert_timestamps(text_raw, TIMESTAMP_SEC)
        transcript_out = next_versioned(transcript_out)
        header = "\n".join([
            "DRAFT — LEGAL INFORMATION ONLY — CLIENT REVIEW REQUIRED",
            f"Case: {case_id}", f"Audio: {audio_in.name}", f"SHA256: {audio_sha}",
            f"Region: {SPEECH_REGION}", f"Language: {lang}", f"Duration: {human_dur(dur)}",
            f"Transcribed: {now_utc()}", "-" * 72
        ])
        write_text(transcript_out, header + "\n" + text_ts + "\n")

        meta = {
            "case_id": case_id, "audio_file": audio_in.name, "audio_sha256": audio_sha,
            "transcript_file": transcript_out.name, "transcript_sha256": sha256sum(transcript_out),
            "azure_region": SPEECH_REGION, "language": lang, "audio_duration_s": dur,
            "word_count": len(text_raw.split()), "attempts_used": attempts,
            "sdk_path": sdk_version(), "python": sys.version.split()[0], "platform": platform.platform(),
            "converted_temp_wav": converted, "timestamp_utc": now_utc()
        }
        write_text(log_json, json.dumps(meta, indent=2, ensure_ascii=False))
        append_jsonl(audit_jsonl, {"ts": now_utc(), "case_id": case_id, "event": "transcribed", "exit": 0, **meta})
        with open(log_txt, "a", encoding="utf-8") as f:
            f.write(f"{now_utc()} DONE | out={transcript_out.name}\n")

        # One-line JSON for stdout
        summary = {
            "status": "ok",
            "transcript_file": str(transcript_out),
            "region": SPEECH_REGION,
            "language": lang,
            "attempts": attempts,
            "duration_s": dur
        }
        print(json.dumps(summary), flush=True)
        sys.exit(0)
    finally:
        try:
            if converted and wav and wav.exists() and not KEEP_TEMP_WAV:
                wav.unlink()
        except Exception:
            pass

if __name__ == "__main__":
    main()
