from __future__ import annotations

import json
from functools import lru_cache

from rdspan import config

TENSE_EN: dict[tuple[str, str], str] = {
    ("presente", "indicativo"): "present indicative",
    ("imperfecto", "indicativo"): "imperfect indicative",
    ("pretérito", "indicativo"): "preterite indicative",
    ("futuro", "indicativo"): "future indicative",
    ("condicional", "indicativo"): "conditional",
    ("presente", "subjuntivo"): "present subjunctive",
    ("imperfecto", "subjuntivo"): "imperfect subjunctive",
}


@lru_cache(maxsize=1)
def lemma_glosses() -> dict[str, str]:
    path = config.data_dir() / "lemma_en.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("lemma_en.json must be an object")
    return {str(k): str(v) for k, v in raw.items()}


def lemma_en(lemma: str) -> str:
    return lemma_glosses().get(lemma, "")


def tense_en(tense: str, mood: str) -> str:
    return TENSE_EN.get((tense, mood), "")
