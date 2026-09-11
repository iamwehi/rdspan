from pathlib import Path

from rdspan.seed import load_paradigms, load_phrases

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    ("hablar", "presente"): ["hablo", "hablas", "habla", "hablamos", "habláis", "hablan"],
    ("hablar", "pretérito"): ["hablé", "hablaste", "habló", "hablamos", "hablasteis", "hablaron"],
    ("comer", "presente"): ["como", "comes", "come", "comemos", "coméis", "comen"],
    ("comer", "pretérito"): ["comí", "comiste", "comió", "comimos", "comisteis", "comieron"],
    ("vivir", "presente"): ["vivo", "vives", "vive", "vivimos", "vivís", "viven"],
    ("vivir", "pretérito"): ["viví", "viviste", "vivió", "vivimos", "vivisteis", "vivieron"],
    ("ser", "presente"): ["soy", "eres", "es", "somos", "sois", "son"],
    ("ser", "pretérito"): ["fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron"],
    ("estar", "presente"): ["estoy", "estás", "está", "estamos", "estáis", "están"],
    ("estar", "pretérito"): ["estuve", "estuviste", "estuvo", "estuvimos", "estuvisteis", "estuvieron"],
    ("ir", "presente"): ["voy", "vas", "va", "vamos", "vais", "van"],
    ("ir", "pretérito"): ["fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron"],
    ("haber", "presente"): ["he", "has", "ha", "hemos", "habéis", "han"],
    ("haber", "pretérito"): ["hube", "hubiste", "hubo", "hubimos", "hubisteis", "hubieron"],
    ("tener", "presente"): ["tengo", "tienes", "tiene", "tenemos", "tenéis", "tienen"],
    ("tener", "pretérito"): ["tuve", "tuviste", "tuvo", "tuvimos", "tuvisteis", "tuvieron"],
    ("hacer", "presente"): ["hago", "haces", "hace", "hacemos", "hacéis", "hacen"],
    ("hacer", "pretérito"): ["hice", "hiciste", "hizo", "hicimos", "hicisteis", "hicieron"],
    ("decir", "presente"): ["digo", "dices", "dice", "decimos", "decís", "dicen"],
    ("decir", "pretérito"): ["dije", "dijiste", "dijo", "dijimos", "dijisteis", "dijeron"],
    ("poder", "presente"): ["puedo", "puedes", "puede", "podemos", "podéis", "pueden"],
    ("poder", "pretérito"): ["pude", "pudiste", "pudo", "pudimos", "pudisteis", "pudieron"],
    ("querer", "presente"): ["quiero", "quieres", "quiere", "queremos", "queréis", "quieren"],
    ("querer", "pretérito"): ["quise", "quisiste", "quiso", "quisimos", "quisisteis", "quisieron"],
    ("venir", "presente"): ["vengo", "vienes", "viene", "venimos", "venís", "vienen"],
    ("venir", "pretérito"): ["vine", "viniste", "vino", "vinimos", "vinisteis", "vinieron"],
}


def test_every_paradigm_has_provenance():
    for p in load_paradigms():
        assert p["source"]
        assert p["license"]
        assert p["verified_at"]
        assert len(p["cells"]) == 6


def test_curated_forms_match_checksum():
    got = {}
    for p in load_paradigms():
        got[(p["lemma"], p["tense"])] = [c["form"] for c in p["cells"]]
    assert got == EXPECTED


def test_phrases_have_provenance():
    phrases = load_phrases()
    assert len(phrases) >= 8
    for ph in phrases:
        assert ph["source"] and ph["license"] and ph["verified_at"]


def test_seed_module_does_not_generate_forms():
    text = (ROOT / "rdspan" / "seed.py").read_text(encoding="utf-8")
    assert "load_paradigms" in text
    for banned in ("conjugate", "openai", "anthropic", "llm", "stem +"):
        assert banned not in text.lower()
