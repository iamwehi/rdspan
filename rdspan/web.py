from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from rdspan import config
from rdspan.auth import AuthMiddleware
from rdspan.db import connect, get_or_create_user, migrate
from rdspan.drills import IllegalTransition, ScriptoriumMachine
from rdspan.matching import token_match
from rdspan.seed import seed
from rdspan.store import (
    ack_paradigm_repeat,
    apply_paradigm_machine,
    ensure_scorecard,
    ensure_scriptorium_page,
    get_or_create_paradigm_drill,
    get_or_create_scriptorium_drill,
    home_paradigms,
    home_phrases,
    load_cells,
    next_paradigm,
    paradigm_machine,
    progress_summary,
    record_attempt,
)
from rdspan.i18n import lemma_en, tense_en
from rdspan.tts import cell_wav, phrase_wav, prefer_audio

STATE_ES = {
    "idle": "inactivo",
    "preview": "vista previa",
    "recite": "recitar",
    "scored": "puntuado",
    "mastered": "dominado",
    "listen": "oír",
    "say": "decir",
    "write": "escribir",
    "done": "hecho",
}

SAFE_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_TENSE_SLUG = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def tense_anchor(tense: str, mood: str) -> str:
    return f"{tense.translate(_TENSE_SLUG)}-{mood}".replace(" ", "-")


def _check_id(value: str) -> str:
    if not value or any(ch not in SAFE_ID for ch in value):
        raise HTTPException(404, "Not found")
    return value


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def current_user(request: Request) -> str:
    user = getattr(request.state, "username", None)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="rdspan"'},
        )
    return user


Db = Annotated[sqlite3.Connection, Depends(get_db)]
UserName = Annotated[str, Depends(current_user)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    try:
        migrate(conn)
        seed(conn)
        get_or_create_user(conn, config.basic_auth_user())
        conn.commit()
    finally:
        conn.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="rdspan", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.add_middleware(AuthMiddleware)
    templates = Jinja2Templates(directory=str(config.templates_dir()))
    templates.env.globals["state_es"] = lambda s: STATE_ES.get(s, s)
    templates.env.globals["tense_anchor"] = tense_anchor
    templates.env.globals["lemma_en"] = lemma_en
    templates.env.globals["tense_en"] = tense_en
    static = config.static_dir()
    if static.is_dir():
        app.mount("/static", StaticFiles(directory=str(static)), name="static")

    def user_row(conn: sqlite3.Connection, username: str) -> sqlite3.Row:
        return get_or_create_user(conn, username)

    def render(request: Request, name: str, ctx: dict, status_code: int = 200) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request, name=name, context=ctx, status_code=status_code
        )

    def is_htmx(request: Request) -> bool:
        return request.headers.get("HX-Request") == "true"

    def cell_audio_url(paradigm_id: str, slot: str) -> str | None:
        path = prefer_audio(cell_wav(paradigm_id, slot))
        if path is None:
            return None
        return f"/audio/cells/{paradigm_id}/{slot}"

    def phrase_audio_url(phrase_id: str) -> str | None:
        path = prefer_audio(phrase_wav(phrase_id))
        if path is None:
            return None
        return f"/audio/phrases/{phrase_id}"

    def paradigm_context(conn: sqlite3.Connection, user_id: int, paradigm_id: str) -> dict:
        paradigm = conn.execute(
            "SELECT * FROM paradigms WHERE id = ?", (paradigm_id,)
        ).fetchone()
        if not paradigm:
            raise HTTPException(404, "Unknown paradigm")
        drill = get_or_create_paradigm_drill(conn, user_id, paradigm_id)
        scorecard = ensure_scorecard(conn, user_id, paradigm_id)
        machine = paradigm_machine(scorecard, drill)
        if machine.state in ("idle", "recite"):
            machine = machine.open()
            apply_paradigm_machine(conn, user_id, paradigm_id, drill, machine)
            drill = get_or_create_paradigm_drill(conn, user_id, paradigm_id)
        cells = load_cells(conn, paradigm_id)
        return {
            "paradigm": paradigm,
            "drill": drill,
            "scorecard": scorecard,
            "machine": machine,
            "cells": cells,
            "remaining": machine.remaining,
            "full_audio": cell_audio_url(paradigm_id, "full"),
            "feedback": None,
            "next_item": next_paradigm(conn, paradigm_id),
        }

    def scriptorium_context(conn: sqlite3.Connection, user_id: int, page_id: str) -> dict:
        phrase = conn.execute("SELECT * FROM phrases WHERE id = ?", (page_id,)).fetchone()
        if not phrase:
            raise HTTPException(404, "Unknown page")
        drill = get_or_create_scriptorium_drill(conn, user_id, page_id)
        page = ensure_scriptorium_page(conn, user_id, page_id)
        machine = ScriptoriumMachine(
            drill["state"],
            bool(page["listen_ok"]),
            bool(page["say_ok"]),
            bool(page["write_ok"]),
        )
        if machine.state == "idle":
            machine = machine.open()
            conn.execute(
                "UPDATE drills SET state = ?, updated_at = datetime('now') WHERE id = ?",
                (machine.state, drill["id"]),
            )
            drill = get_or_create_scriptorium_drill(conn, user_id, page_id)
        return {
            "phrase": phrase,
            "drill": drill,
            "page": page,
            "machine": machine,
            "audio": phrase_audio_url(page_id),
            "feedback": None,
            "complete": machine.complete,
        }

    def save_scriptorium(
        conn: sqlite3.Connection,
        user_id: int,
        page_id: str,
        drill_id: int,
        machine: ScriptoriumMachine,
    ) -> None:
        conn.execute(
            "UPDATE drills SET state = ?, updated_at = datetime('now') WHERE id = ?",
            (machine.state, drill_id),
        )
        conn.execute(
            """
            UPDATE scriptorium_pages
            SET listen_ok = ?, say_ok = ?, write_ok = ?
            WHERE user_id = ? AND page_id = ?
            """,
            (
                int(machine.listen_ok),
                int(machine.say_ok),
                int(machine.write_ok),
                user_id,
                page_id,
            ),
        )

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, conn: Db, username: UserName):
        user = user_row(conn, username)
        paradigms = home_paradigms(conn, user["id"])
        grouped: list[dict] = []
        for row in paradigms:
            if not grouped or grouped[-1]["lemma"] != row["lemma"]:
                grouped.append({"lemma": row["lemma"], "regularity": row["regularity"], "rows": []})
            grouped[-1]["rows"].append(row)
        phrases = home_phrases(conn, user["id"])
        return render(
            request,
            "home.html",
            {
                "summary": progress_summary(conn, user["id"]),
                "grouped": grouped,
                "phrases": phrases,
                "target": config.scorecard_target(),
            },
        )

    @app.get("/tiempos", response_class=HTMLResponse)
    def tenses_page(request: Request, username: UserName):
        return render(request, "tenses.html", {})

    @app.get("/paradigms/{paradigm_id}", response_class=HTMLResponse)
    def paradigm_page(request: Request, paradigm_id: str, conn: Db, username: UserName):
        paradigm_id = _check_id(paradigm_id)
        user = user_row(conn, username)
        ctx = paradigm_context(conn, user["id"], paradigm_id)
        return render(request, "paradigm.html", ctx)

    @app.post("/paradigms/{paradigm_id}/next")
    def paradigm_next(paradigm_id: str, conn: Db, username: UserName):
        paradigm_id = _check_id(paradigm_id)
        user = user_row(conn, username)
        ctx = paradigm_context(conn, user["id"], paradigm_id)
        ack_paradigm_repeat(conn, user["id"], paradigm_id)
        nxt = ctx["next_item"]
        return RedirectResponse(f"/paradigms/{nxt['id']}", status_code=303)

    @app.get("/scriptorium/{page_id}", response_class=HTMLResponse)
    def scriptorium_page(request: Request, page_id: str, conn: Db, username: UserName):
        page_id = _check_id(page_id)
        user = user_row(conn, username)
        return render(request, "scriptorium.html", scriptorium_context(conn, user["id"], page_id))

    def scriptorium_fragment(request: Request, ctx: dict) -> HTMLResponse:
        name = "partials/scriptorium_drill.html" if is_htmx(request) else "scriptorium.html"
        return render(request, name, ctx)

    @app.post("/scriptorium/{page_id}/listen", response_class=HTMLResponse)
    def scriptorium_listen(request: Request, page_id: str, conn: Db, username: UserName):
        page_id = _check_id(page_id)
        user = user_row(conn, username)
        ctx = scriptorium_context(conn, user["id"], page_id)
        try:
            nxt = ctx["machine"].ack_listen()
        except IllegalTransition as exc:
            ctx["feedback"] = {"kind": "bad", "text": str(exc)}
            return scriptorium_fragment(request, ctx)
        record_attempt(conn, user["id"], ctx["drill"]["id"], "listen", True, None)
        save_scriptorium(conn, user["id"], page_id, ctx["drill"]["id"], nxt)
        ctx = scriptorium_context(conn, user["id"], page_id)
        ctx["feedback"] = {"kind": "ok", "text": "Oído. Di la frase en voz alta y escríbela."}
        return scriptorium_fragment(request, ctx)

    @app.post("/scriptorium/{page_id}/say", response_class=HTMLResponse)
    def scriptorium_say(
        request: Request,
        page_id: str,
        conn: Db,
        username: UserName,
        response: Annotated[str, Form()] = "",
    ):
        page_id = _check_id(page_id)
        user = user_row(conn, username)
        ctx = scriptorium_context(conn, user["id"], page_id)
        passed = token_match(ctx["phrase"]["text"], response)
        try:
            nxt = ctx["machine"].score_say(passed)
        except IllegalTransition as exc:
            ctx["feedback"] = {"kind": "bad", "text": str(exc)}
            return scriptorium_fragment(request, ctx)
        record_attempt(conn, user["id"], ctx["drill"]["id"], "say", passed, response)
        save_scriptorium(conn, user["id"], page_id, ctx["drill"]["id"], nxt)
        ctx = scriptorium_context(conn, user["id"], page_id)
        ctx["last_response"] = "" if passed else response
        if passed:
            ctx["feedback"] = {"kind": "ok", "text": "Bien. Ahora escríbela de memoria."}
        else:
            ctx["feedback"] = {"kind": "bad", "text": "No coincide. Dila otra vez y escríbela."}
        return scriptorium_fragment(request, ctx)

    @app.post("/scriptorium/{page_id}/write", response_class=HTMLResponse)
    def scriptorium_write(
        request: Request,
        page_id: str,
        conn: Db,
        username: UserName,
        response: Annotated[str, Form()] = "",
    ):
        page_id = _check_id(page_id)
        user = user_row(conn, username)
        ctx = scriptorium_context(conn, user["id"], page_id)
        passed = token_match(ctx["phrase"]["text"], response)
        try:
            nxt = ctx["machine"].score_write(passed)
        except IllegalTransition as exc:
            ctx["feedback"] = {"kind": "bad", "text": str(exc)}
            return scriptorium_fragment(request, ctx)
        record_attempt(conn, user["id"], ctx["drill"]["id"], "write", passed, response)
        save_scriptorium(conn, user["id"], page_id, ctx["drill"]["id"], nxt)
        ctx = scriptorium_context(conn, user["id"], page_id)
        ctx["last_response"] = "" if passed else response
        if passed:
            ctx["feedback"] = {"kind": "ok", "text": "Página completa: oír, decir y escribir."}
        else:
            ctx["feedback"] = {"kind": "bad", "text": "No coincide. Escríbela otra vez de memoria."}
        return scriptorium_fragment(request, ctx)

    @app.get("/audio/cells/{paradigm_id}/{slot}")
    def serve_cell_audio(paradigm_id: str, slot: str, username: UserName):
        paradigm_id = _check_id(paradigm_id)
        slot = _check_id(slot)
        path = prefer_audio(cell_wav(paradigm_id, slot))
        if path is None:
            raise HTTPException(404, "Audio not generated")
        media = "audio/ogg" if path.suffix == ".ogg" else "audio/wav"
        return FileResponse(path, media_type=media)

    @app.get("/audio/phrases/{phrase_id}")
    def serve_phrase_audio(phrase_id: str, username: UserName):
        phrase_id = _check_id(phrase_id)
        path = prefer_audio(phrase_wav(phrase_id))
        if path is None:
            raise HTTPException(404, "Audio not generated")
        media = "audio/ogg" if path.suffix == ".ogg" else "audio/wav"
        return FileResponse(path, media_type=media)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


app = create_app()
