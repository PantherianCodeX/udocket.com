from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from packages.udocket_core.json_utils import parse_json_object


def _parse_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value))
    except Exception:
        return None


def _parse_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(float(value))
    except Exception:
        return None


def probe_audio_metadata(source: str | Path) -> Dict[str, Optional[Any]]:
    """Return ffprobe-derived audio metadata.

    Keys follow the naming used by job telemetry helpers so the result can be
    merged directly into per-job metadata JSON files or database fields.
    """

    path = Path(source)
    try:
        path = path.expanduser().resolve()
    except Exception:
        pass

    if not path.exists():
        return {}
    if shutil.which("ffprobe") is None:
        return {}

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-select_streams",
        "a:0",
        "-show_streams",
        "-show_format",
        str(path),
    ]

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        data = parse_json_object(out, context="ffprobe output")
    except Exception:
        return {}

    streams_value = data.get("streams")
    if not isinstance(streams_value, list) or not streams_value:
        return {}
    stream_candidate = streams_value[0]
    if not isinstance(stream_candidate, dict):
        return {}
    stream = stream_candidate

    fmt_value = data.get("format")
    fmt = fmt_value if isinstance(fmt_value, dict) else {}

    duration = _parse_float(stream.get("duration")) or _parse_float(fmt.get("duration"))
    bitrate = _parse_int(stream.get("bit_rate") or fmt.get("bit_rate"))
    channels = _parse_int(stream.get("channels"))
    sample_rate = _parse_int(stream.get("sample_rate"))

    sample_fmt = stream.get("sample_fmt")
    bits_per = _parse_int(stream.get("bits_per_raw_sample") or stream.get("bits_per_sample"))

    return {
        "audio_duration_s": duration,
        "audio_bitrate_kbps": int(round(bitrate / 1000)) if isinstance(bitrate, int) and bitrate > 0 else None,
        "audio_channels": channels,
        "audio_sample_rate_hz": sample_rate,
        "audio_codec": stream.get("codec_name"),
        "audio_channel_layout": stream.get("channel_layout"),
        "audio_sample_fmt": sample_fmt,
        "audio_bits_per_sample": bits_per,
    }
