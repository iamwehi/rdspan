from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "rdspan.db"))
    monkeypatch.setenv("AUDIO_PATH", str(tmp_path / "audio"))
    monkeypatch.setenv("BASIC_AUTH_USER", "tester")
    monkeypatch.setenv("BASIC_AUTH_PASS", "secret")
    monkeypatch.setenv("SCORECARD_TARGET", "3")
    from rdspan.web import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def auth() -> tuple[str, str]:
    return ("tester", "secret")
