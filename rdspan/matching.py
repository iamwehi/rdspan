"""Exact token match for say/write: ignore punctuation and case, keep accents."""

from __future__ import annotations

import re
import unicodedata

_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFC", text or "")
    lowered = decomposed.casefold()
    stripped = _PUNCT_RE.sub(" ", lowered)
    return _SPACE_RE.sub(" ", stripped).strip()


def tokens(text: str) -> list[str]:
    norm = normalize_text(text)
    if not norm:
        return []
    return norm.split(" ")


def token_match(expected: str, actual: str) -> bool:
    return tokens(expected) == tokens(actual)


def cell_match(form: str, pronoun: str, actual: str) -> bool:
    """Accept the bare form, or the pronoun followed by the form."""
    got = tokens(actual)
    want = tokens(form)
    if got == want:
        return True
    return got == tokens(pronoun) + want


def all_cells_match(
    cells: list[tuple[str, str, str]],
    answers: dict[str, str],
) -> tuple[bool, dict[str, bool]]:
    per_slot: dict[str, bool] = {}
    ok = True
    for slot, form, pronoun in cells:
        passed = cell_match(form, pronoun, answers.get(slot, ""))
        per_slot[slot] = passed
        if not passed:
            ok = False
    return ok, per_slot
