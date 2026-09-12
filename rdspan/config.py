from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    override = os.environ.get("RDSPAN_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parent.parent


def database_path() -> Path:
    raw = os.environ.get("DATABASE_PATH")
    if raw:
        return Path(raw).resolve()
    return (project_root() / "var" / "rdspan.db").resolve()


def audio_path() -> Path:
    raw = os.environ.get("AUDIO_PATH")
    if raw:
        return Path(raw).resolve()
    return (project_root() / "data" / "audio").resolve()


def data_dir() -> Path:
    return project_root() / "data"


def migrations_dir() -> Path:
    return project_root() / "migrations"


def templates_dir() -> Path:
    return project_root() / "templates"


def static_dir() -> Path:
    return project_root() / "static"


def basic_auth_user() -> str:
    return os.environ.get("BASIC_AUTH_USER", "rdspan")


def basic_auth_pass() -> str:
    return os.environ.get("BASIC_AUTH_PASS", "changeme")


def scorecard_target() -> int:
    return int(os.environ.get("SCORECARD_TARGET", "100"))


def piper_voice() -> str:
    return os.environ.get("PIPER_VOICE", "es_ES-davefx-medium")


def piper_length_scale() -> float:
    return float(os.environ.get("PIPER_LENGTH_SCALE", "1.35"))


def full_audio_pause_ms() -> int:
    """Silence between forms on the full-table track, so the listener can repeat."""
    return int(os.environ.get("FULL_AUDIO_PAUSE_MS", "2000"))


def host() -> str:
    return os.environ.get("HOST", "0.0.0.0")


def port() -> int:
    return int(os.environ.get("PORT", "8080"))
