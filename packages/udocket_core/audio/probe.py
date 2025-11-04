from __future__ import annotations

# pyright: strict
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

from packages.udocket_common.json_utils import (
    JSONObject,
    JSONValue,
    coerce_json_object,
    coerce_object_list,
    coerce_str,
    parse_json_object,
)


class AudioMetadata(TypedDict, total=False):
    audio_duration_s: float | None
    audio_bitrate_kbps: int | None
    audio_channels: int | None
    audio_sample_rate_hz: int | None
    audio_codec: str | None
    audio_channel_layout: str | None
    audio_sample_fmt: str | None
    audio_bits_per_sample: int | None


def _parse_float(value: JSONValue | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _parse_int(value: JSONValue | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _coerce_mapping(value: JSONValue | None) -> JSONObject:
    if isinstance(value, Mapping):
        return coerce_json_object(value)
    return {}


def probe_audio_metadata(source: str | Path) -> AudioMetadata:
    """Return ffprobe-derived audio metadata."""

    path = Path(source)
    try:
        path = path.expanduser().resolve()
    except OSError:
        pass

    metadata: AudioMetadata = {}
    if not path.exists():
        return metadata
    if shutil.which("ffprobe") is None:
        return metadata

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
    except (subprocess.CalledProcessError, ValueError):
        return metadata

    streams = coerce_object_list(data.get("streams"))
    if not streams:
        return metadata
    stream = streams[0]
    if not stream:
        return metadata

    fmt = _coerce_mapping(data.get("format"))

    duration = _parse_float(stream.get("duration")) or _parse_float(fmt.get("duration"))
    bitrate = _parse_int(stream.get("bit_rate"))
    if bitrate is None:
        bitrate = _parse_int(fmt.get("bit_rate"))
    channels = _parse_int(stream.get("channels"))
    sample_rate = _parse_int(stream.get("sample_rate"))

    bits_per = _parse_int(stream.get("bits_per_raw_sample"))
    if bits_per is None:
        bits_per = _parse_int(stream.get("bits_per_sample"))

    metadata["audio_duration_s"] = duration
    metadata["audio_bitrate_kbps"] = (
        int(round(bitrate / 1000)) if isinstance(bitrate, int) and bitrate > 0 else None
    )
    metadata["audio_channels"] = channels
    metadata["audio_sample_rate_hz"] = sample_rate
    metadata["audio_codec"] = coerce_str(stream.get("codec_name"))
    metadata["audio_channel_layout"] = coerce_str(stream.get("channel_layout"))
    metadata["audio_sample_fmt"] = coerce_str(stream.get("sample_fmt"))
    metadata["audio_bits_per_sample"] = bits_per

    return metadata
