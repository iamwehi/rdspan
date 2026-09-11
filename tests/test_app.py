from __future__ import annotations

from fastapi.testclient import TestClient

HABLAR = {
    "slot_1s": "hablo",
    "slot_2s": "hablas",
    "slot_3s": "habla",
    "slot_1p": "hablamos",
    "slot_2p": "habláis",
    "slot_3p": "hablan",
}


def test_requires_basic_auth(client: TestClient):
    assert client.get("/").status_code == 401
    assert "WWW-Authenticate" in client.get("/").headers


def test_home_lists_curated_verbs(client: TestClient, auth: tuple[str, str]):
    r = client.get("/", auth=auth)
    assert r.status_code == 200
    assert "hablar" in r.text
    assert "scriptorium" in r.text.lower()
    assert "streak" not in r.text.lower()
    assert "reps de paradigmas" in r.text


def test_paradigm_rep_counts_only_after_passing_recite(
    client: TestClient, auth: tuple[str, str]
):
    pid = "hablar.presente.indicativo"
    assert client.get(f"/paradigms/{pid}", auth=auth).status_code == 200

    wrong = {**HABLAR, "slot_1s": "hago"}
    client.post(f"/paradigms/{pid}/recite", auth=auth)
    failed = client.post(f"/paradigms/{pid}/score", data={**wrong, "mode": "say"}, auth=auth)
    assert failed.status_code == 200
    assert "0 / 3" in failed.text or "3 reps para" in failed.text

    client.post(f"/paradigms/{pid}/recite", auth=auth)
    write = client.post(
        f"/paradigms/{pid}/score", data={**HABLAR, "mode": "write"}, auth=auth
    )
    assert "no suma" in write.text.lower()

    client.post(f"/paradigms/{pid}/recite", auth=auth)
    passed = client.post(
        f"/paradigms/{pid}/score", data={**HABLAR, "mode": "say"}, auth=auth
    )
    assert passed.status_code == 200
    assert "1 / 3" in passed.text
    assert "para la meta" in passed.text


def test_scriptorium_requires_listen_say_write(
    client: TestClient, auth: tuple[str, str]
):
    page = "p01"
    home = client.get("/", auth=auth).text
    assert "oír" in home

    r = client.get(f"/scriptorium/{page}", auth=auth)
    assert r.status_code == 200
    assert "Yo soy estudiante." in r.text

    say_early = client.post(
        f"/scriptorium/{page}/say", data={"response": "Yo soy estudiante."}, auth=auth
    )
    assert "después de oírla" in say_early.text

    client.post(f"/scriptorium/{page}/listen", auth=auth)
    missed = client.post(
        f"/scriptorium/{page}/say", data={"response": "soy profesor"}, auth=auth
    )
    assert "No coincide" in missed.text

    said = client.post(
        f"/scriptorium/{page}/say", data={"response": "yo soy estudiante"}, auth=auth
    )
    assert "de memoria" in said.text
    assert 'value="yo soy estudiante"' not in said.text
    done = client.post(
        f"/scriptorium/{page}/write", data={"response": "Yo soy estudiante."}, auth=auth
    )
    assert "Página completa" in done.text
    home = client.get("/", auth=auth).text
    assert home.count('class="on"') >= 3


def test_session_cookie_covers_htmx_posts(client: TestClient, auth: tuple[str, str]):
    first = client.get("/", auth=auth)
    assert first.status_code == 200
    assert client.get("/").status_code == 200
