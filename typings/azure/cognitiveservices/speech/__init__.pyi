from __future__ import annotations

from typing import Any

__version__: str

class PropertyId:
    Speech_LogFilename: int

class ProfanityOption:
    Masked: int

class SpeechConfig:
    speech_recognition_language: str

    def __init__(self, subscription: str, region: str) -> None: ...
    def set_property(self, id: Any, value: str) -> None: ...
    def request_word_level_timestamps(self) -> None: ...
    def set_profanity(self, option: Any) -> None: ...

class _Signal:
    def connect(self, handler: Any) -> None: ...

class SpeechRecognizer:
    recognizing: _Signal
    recognized: _Signal
    cancelled: _Signal
    session_stopped: _Signal

    def __init__(self, *, speech_config: SpeechConfig, audio_config: Any) -> None: ...
    def start_continuous_recognition(self) -> None: ...
    def stop_continuous_recognition(self) -> None: ...

class ResultReason:
    RecognizedSpeech: int

class audio:
    class AudioConfig:
        def __init__(self, *, filename: str) -> None: ...

