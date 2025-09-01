from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    # Azure
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str = "canadacentral"
    LANGUAGE: str = "en-CA"

    # Paths
    STORAGE_ROOT: Path = Path("/app/storage")
    MAX_UPLOAD_MB: int = 500

    # API/Admin
    API_BIND: str = "0.0.0.0"
    API_PORT: int = 8080
    ADMIN_BIND: str = "0.0.0.0"
    ADMIN_PORT: int = 8081

    # DB
    DATABASE_URL: str = "sqlite:///__AUTO__"

    # Worker
    POLL_INTERVAL_SEC: int = 2
    JOB_TIMEOUT_SEC: int = 7200
    MAX_CONCURRENT: int = 1

    # Agent
    AGENT_CMD_TEMPLATE: str = (
        'python packages/udocket_core/agents/transcribe.py --input "{audio}" --case "{case_id}" --outdir "{case_dir}/transcript" --language "{lang}"'
    )

    # Security
    ALLOWED_AUDIO_MIME: str = (
        "audio/wav,audio/x-wav,audio/mpeg,audio/mp4,audio/aac,audio/ogg,audio/flac,audio/x-flac"
    )

    @field_validator("AZURE_SPEECH_REGION")
    def _ca_only(cls, v):
        if v not in ("canadacentral", "canadaeast"):
            raise ValueError("AZURE_SPEECH_REGION must be canadacentral or canadaeast")
        return v

    @model_validator(mode="before")
    def _sqlite_auto(cls, data):
        if isinstance(data, dict):
            v = data.get("DATABASE_URL")
            if v == "sqlite:///__AUTO__":
                root = data.get("STORAGE_ROOT", Path("/app/storage"))
                data["DATABASE_URL"] = f"sqlite:///{Path(root) / 'udocket.db'}"
        return data

settings = Settings(_env_file=".env", _env_file_encoding="utf-8")
