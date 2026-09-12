from __future__ import annotations

from fastapi.testclient import TestClient

def test_requires_basic_auth(client: TestClient):
    assert client.get("/").status_code == 401
    assert "WWW-Authenticate" in client.get("/").headers


def test_home_lists_curated_verbs(client: TestClient, auth: tuple[str, str]):
    r = client.get("/", auth=auth)
    assert r.status_code == 200
    assert "hablar" in r.text
    assert "pretérito" in r.text
    assert "subjuntivo" in r.text
    assert "Scriptorium" not in r.text
    assert "streak" not in r.text.lower()
    assert "reps de paradigmas" in r.text
    assert "Escucha, repite, siguiente" in r.text
    assert "/tiempos" in r.text
    assert "to speak" in r.text
    assert "present indicative" in r.text
    assert 'class="pill regular"' in r.text
    assert 'class="pill irregular"' in r.text


def test_paradigm_loop_is_hear_repeat_next(
    client: TestClient, auth: tuple[str, str]
):
    pid = "hablar.presente.indicativo"
    page = client.get(f"/paradigms/{pid}", auth=auth)
    assert page.status_code == 200
    assert "Escritura opcional" not in page.text
    assert "slot_1s" not in page.text
    assert "Recitar sin mirar" not in page.text
    assert "Escucha. Repite en voz alta. Siguiente." in page.text
    assert "to speak" in page.text
    assert "present indicative" in page.text
    assert 'class="pill regular"' in page.text
    assert "Siguiente ·" in page.text
    assert "<th>Audio</th>" not in page.text
    assert "Oír yo" not in page.text

    irregular = client.get("/paradigms/ser.presente.indicativo", auth=auth)
    assert irregular.status_code == 200
    assert 'class="pill irregular"' in irregular.text

    nxt = client.post(f"/paradigms/{pid}/next", auth=auth, follow_redirects=False)
    assert nxt.status_code == 303
    location = nxt.headers["location"]
    assert location.startswith("/paradigms/")
    assert location != f"/paradigms/{pid}"
    assert "hablar.imperfecto.indicativo" in location

    scored = client.get(f"/paradigms/{pid}", auth=auth)
    assert "1 / 3" in scored.text
    assert "para la meta" in scored.text

    missing = client.post(f"/paradigms/{pid}/score", auth=auth)
    assert missing.status_code == 404


def test_tenses_page_explains_each_used_tense(
    client: TestClient, auth: tuple[str, str]
):
    r = client.get("/tiempos", auth=auth)
    assert r.status_code == 200
    body = r.text.lower()
    for needle in (
        "presente de indicativo",
        "imperfecto de indicativo",
        "pretérito de indicativo",
        "futuro de indicativo",
        "condicional",
        "presente de subjuntivo",
        "imperfecto de subjuntivo",
    ):
        assert needle in body
    assert 'id="preterito-indicativo"' in r.text
    for needle in (
        "present indicative",
        "imperfect indicative",
        "preterite indicative",
        "future indicative",
        "conditional",
        "present subjunctive",
        "imperfect subjunctive",
        "tenses in the tables",
        "what is happening now",
        "ongoing or repeated past",
        "finished past events",
        "what will happen",
        "what would happen",
        "wishes, doubts",
        "past or hypothetical",
    ):
        assert needle in body


def test_scriptorium_is_absent_without_phrases(
    client: TestClient, auth: tuple[str, str]
):
    home = client.get("/", auth=auth)
    assert home.status_code == 200
    assert "/scriptorium/" not in home.text
    missing = client.get("/scriptorium/p01", auth=auth)
    assert missing.status_code == 404


def test_session_cookie_covers_htmx_posts(client: TestClient, auth: tuple[str, str]):
    first = client.get("/", auth=auth)
    assert first.status_code == 200
    assert client.get("/").status_code == 200
