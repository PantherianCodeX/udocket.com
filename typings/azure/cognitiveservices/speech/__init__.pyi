from __future__ import annotations

from typing import Any, Callable, Optional

from .audio import AudioConfig


class PropertyId:
    Speech_LogFilename: "PropertyId"


class ProfanityOption:
    Masked: "ProfanityOption"


class ResultReason:
    RecognizedSpeech: "ResultReason"
    NoMatch: "ResultReason"
    Canceled: "ResultReason"


class CancellationReason:
    Error: "CancellationReason"


class EventSignal:
    def connect(self, handler: Callable[..., Any]) -> None: ...


class SpeechRecognitionResult:
    reason: ResultReason
    text: str
    offset: int
    duration: int


class CancellationDetails:
    reason: CancellationReason
    error_details: Optional[str]

    @staticmethod
    def from_result(result: SpeechRecognitionResult) -> "CancellationDetails": ...


class SpeechConfig:
    speech_recognition_language: str

    def __init__(self, *, subscription: str, region: str) -> None: ...

    def set_property(self, property_id: PropertyId, value: str) -> None: ...

    def request_word_level_timestamps(self) -> None: ...

    def set_profanity(self, option: ProfanityOption) -> None: ...


class SpeechRecognizer:
    recognizing: EventSignal
    recognized: EventSignal
    cancelled: EventSignal
    session_stopped: EventSignal

    def __init__(self, *, speech_config: SpeechConfig, audio_config: AudioConfig) -> None: ...

    def recognize_once(self) -> SpeechRecognitionResult: ...

    def start_continuous_recognition(self) -> None: ...

    def stop_continuous_recognition(self) -> None: ...
