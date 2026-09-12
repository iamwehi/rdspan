import importlib.util
from collections import defaultdict
from pathlib import Path

from rdspan.db import connect, migrate
from rdspan.seed import load_paradigms, load_phrases, seed

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "build_paradigms", ROOT / "scripts" / "build_paradigms.py"
)
_BUILD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_BUILD)

TENSES = _BUILD.TENSES
LEMMAS = [row[0] for row in _BUILD.verb_entries()]

EXPECTED = {
    ("hablar", "presente", "indicativo"): ["hablo", "hablas", "habla", "hablamos", "habláis", "hablan"],
    ("hablar", "imperfecto", "indicativo"): ["hablaba", "hablabas", "hablaba", "hablábamos", "hablabais", "hablaban"],
    ("hablar", "pretérito", "indicativo"): ["hablé", "hablaste", "habló", "hablamos", "hablasteis", "hablaron"],
    ("hablar", "futuro", "indicativo"): ["hablaré", "hablarás", "hablará", "hablaremos", "hablaréis", "hablarán"],
    ("hablar", "condicional", "indicativo"): ["hablaría", "hablarías", "hablaría", "hablaríamos", "hablaríais", "hablarían"],
    ("hablar", "presente", "subjuntivo"): ["hable", "hables", "hable", "hablemos", "habléis", "hablen"],
    ("hablar", "imperfecto", "subjuntivo"): ["hablara", "hablaras", "hablara", "habláramos", "hablarais", "hablaran"],
    ("comer", "presente", "indicativo"): ["como", "comes", "come", "comemos", "coméis", "comen"],
    ("vivir", "presente", "indicativo"): ["vivo", "vives", "vive", "vivimos", "vivís", "viven"],
    ("contar", "presente", "indicativo"): ["cuento", "cuentas", "cuenta", "contamos", "contáis", "cuentan"],
    ("cerrar", "presente", "indicativo"): ["cierro", "cierras", "cierra", "cerramos", "cerráis", "cierran"],
    ("mover", "presente", "indicativo"): ["muevo", "mueves", "mueve", "movemos", "movéis", "mueven"],
    ("perder", "presente", "indicativo"): ["pierdo", "pierdes", "pierde", "perdemos", "perdéis", "pierden"],
    ("pedir", "presente", "indicativo"): ["pido", "pides", "pide", "pedimos", "pedís", "piden"],
    ("pedir", "pretérito", "indicativo"): ["pedí", "pediste", "pidió", "pedimos", "pedisteis", "pidieron"],
    ("pedir", "presente", "subjuntivo"): ["pida", "pidas", "pida", "pidamos", "pidáis", "pidan"],
    ("sentir", "presente", "subjuntivo"): ["sienta", "sientas", "sienta", "sintamos", "sintáis", "sientan"],
    ("dormir", "pretérito", "indicativo"): ["dormí", "dormiste", "durmió", "dormimos", "dormisteis", "durmieron"],
    ("jugar", "presente", "subjuntivo"): ["juegue", "juegues", "juegue", "juguemos", "juguéis", "jueguen"],
    ("construir", "pretérito", "indicativo"): ["construí", "construiste", "construyó", "construimos", "construisteis", "construyeron"],
    ("conocer", "presente", "indicativo"): ["conozco", "conoces", "conoce", "conocemos", "conocéis", "conocen"],
    ("ser", "presente", "indicativo"): ["soy", "eres", "es", "somos", "sois", "son"],
    ("ser", "imperfecto", "indicativo"): ["era", "eras", "era", "éramos", "erais", "eran"],
    ("ser", "pretérito", "indicativo"): ["fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron"],
    ("ser", "presente", "subjuntivo"): ["sea", "seas", "sea", "seamos", "seáis", "sean"],
    ("estar", "presente", "subjuntivo"): ["esté", "estés", "esté", "estemos", "estéis", "estén"],
    ("ir", "imperfecto", "indicativo"): ["iba", "ibas", "iba", "íbamos", "ibais", "iban"],
    ("ir", "presente", "subjuntivo"): ["vaya", "vayas", "vaya", "vayamos", "vayáis", "vayan"],
    ("haber", "presente", "indicativo"): ["he", "has", "ha", "hemos", "habéis", "han"],
    ("haber", "futuro", "indicativo"): ["habré", "habrás", "habrá", "habremos", "habréis", "habrán"],
    ("tener", "futuro", "indicativo"): ["tendré", "tendrás", "tendrá", "tendremos", "tendréis", "tendrán"],
    ("hacer", "pretérito", "indicativo"): ["hice", "hiciste", "hizo", "hicimos", "hicisteis", "hicieron"],
    ("decir", "futuro", "indicativo"): ["diré", "dirás", "dirá", "diremos", "diréis", "dirán"],
    ("poder", "condicional", "indicativo"): ["podría", "podrías", "podría", "podríamos", "podríais", "podrían"],
    ("querer", "pretérito", "indicativo"): ["quise", "quisiste", "quiso", "quisimos", "quisisteis", "quisieron"],
    ("venir", "presente", "indicativo"): ["vengo", "vienes", "viene", "venimos", "venís", "vienen"],
    ("dar", "presente", "subjuntivo"): ["dé", "des", "dé", "demos", "deis", "den"],
    ("ver", "imperfecto", "indicativo"): ["veía", "veías", "veía", "veíamos", "veíais", "veían"],
    ("poner", "pretérito", "indicativo"): ["puse", "pusiste", "puso", "pusimos", "pusisteis", "pusieron"],
    ("saber", "presente", "indicativo"): ["sé", "sabes", "sabe", "sabemos", "sabéis", "saben"],
    ("salir", "futuro", "indicativo"): ["saldré", "saldrás", "saldrá", "saldremos", "saldréis", "saldrán"],
    ("oír", "presente", "indicativo"): ["oigo", "oyes", "oye", "oímos", "oís", "oyen"],
    ("traer", "pretérito", "indicativo"): ["traje", "trajiste", "trajo", "trajimos", "trajisteis", "trajeron"],
    ("andar", "pretérito", "indicativo"): ["anduve", "anduviste", "anduvo", "anduvimos", "anduvisteis", "anduvieron"],
    ("caber", "presente", "indicativo"): ["quepo", "cabes", "cabe", "cabemos", "cabéis", "caben"],
    ("caer", "pretérito", "indicativo"): ["caí", "caíste", "cayó", "caímos", "caísteis", "cayeron"],
    ("producir", "pretérito", "indicativo"): ["produje", "produjiste", "produjo", "produjimos", "produjisteis", "produjeron"],
    ("valer", "futuro", "indicativo"): ["valdré", "valdrás", "valdrá", "valdremos", "valdréis", "valdrán"],
    ("mantener", "presente", "indicativo"): ["mantengo", "mantienes", "mantiene", "mantenemos", "mantenéis", "mantienen"],
    ("almorzar", "presente", "subjuntivo"): ["almuerce", "almuerces", "almuerce", "almorcemos", "almorcéis", "almuercen"],
    ("seguir", "presente", "indicativo"): ["sigo", "sigues", "sigue", "seguimos", "seguís", "siguen"],
    ("seguir", "pretérito", "indicativo"): ["seguí", "seguiste", "siguió", "seguimos", "seguisteis", "siguieron"],
    ("elegir", "presente", "indicativo"): ["elijo", "eliges", "elige", "elegimos", "elegís", "eligen"],
    ("comenzar", "presente", "subjuntivo"): ["comience", "comiences", "comience", "comencemos", "comencéis", "comiencen"],
    ("leer", "pretérito", "indicativo"): ["leí", "leíste", "leyó", "leímos", "leísteis", "leyeron"],
    ("morir", "presente", "indicativo"): ["muero", "mueres", "muere", "morimos", "morís", "mueren"],
    ("oler", "presente", "indicativo"): ["huelo", "hueles", "huele", "olemos", "oléis", "huelen"],
    ("sonreír", "presente", "indicativo"): ["sonrío", "sonríes", "sonríe", "sonreímos", "sonreís", "sonríen"],
    ("gruñir", "pretérito", "indicativo"): ["gruñí", "gruñiste", "gruñó", "gruñimos", "gruñisteis", "gruñeron"],
    ("prever", "presente", "indicativo"): ["preveo", "prevés", "prevé", "prevemos", "prevéis", "prevén"],
    ("satisfacer", "pretérito", "indicativo"): ["satisfice", "satisficiste", "satisfizo", "satisficimos", "satisficisteis", "satisficieron"],
    ("avergonzar", "presente", "indicativo"): ["avergüenzo", "avergüenzas", "avergüenza", "avergonzamos", "avergonzáis", "avergüenzan"],
    ("huir", "presente", "indicativo"): ["huyo", "huyes", "huye", "huimos", "huis", "huyen"],
    ("reír", "pretérito", "indicativo"): ["reí", "reíste", "rio", "reímos", "reísteis", "rieron"],
    ("cocer", "presente", "indicativo"): ["cuezo", "cueces", "cuece", "cocemos", "cocéis", "cuecen"],
    ("conseguir", "presente", "indicativo"): ["consigo", "consigues", "consigue", "conseguimos", "conseguís", "consiguen"],
    ("negar", "presente", "subjuntivo"): ["niegue", "niegues", "niegue", "neguemos", "neguéis", "nieguen"],
    ("adquirir", "presente", "indicativo"): ["adquiero", "adquieres", "adquiere", "adquirimos", "adquirís", "adquieren"],
    ("maldecir", "futuro", "indicativo"): ["maldeciré", "maldecirás", "maldecirá", "maldeciremos", "maldeciréis", "maldecirán"],
    ("soñar", "presente", "indicativo"): ["sueño", "sueñas", "sueña", "soñamos", "soñáis", "sueñan"],
    ("abrir", "presente", "indicativo"): ["abro", "abres", "abre", "abrimos", "abrís", "abren"],
    ("volver", "presente", "indicativo"): ["vuelvo", "vuelves", "vuelve", "volvemos", "volvéis", "vuelven"],
}


def test_every_paradigm_has_provenance():
    for p in load_paradigms():
        assert p["source"]
        assert p["license"]
        assert p["verified_at"]
        assert len(p["cells"]) == 6
        assert "Butt" in p["source"]


def test_seed_is_verbs_only_with_simple_tenses():
    paradigms = load_paradigms()
    by_lemma: dict[str, set[tuple[str, str]]] = defaultdict(set)
    ids = []
    for p in paradigms:
        by_lemma[p["lemma"]].add((p["tense"], p["mood"]))
        ids.append(p["id"])
        assert p["id"].isascii()
    assert list(by_lemma) == LEMMAS
    assert len(LEMMAS) >= 500
    for lemma, tables in by_lemma.items():
        assert tables == set(TENSES), lemma
    assert len(paradigms) == len(LEMMAS) * len(TENSES)
    assert len(set(ids)) == len(ids)
    assert "sonar" in by_lemma and "soñar" in by_lemma


def test_curated_forms_match_checksum():
    got = {}
    for p in load_paradigms():
        got[(p["lemma"], p["tense"], p["mood"])] = [c["form"] for c in p["cells"]]
    for key, forms in EXPECTED.items():
        assert got[key] == forms, key


def test_phrases_seed_is_empty():
    assert load_phrases() == []


def test_seed_module_does_not_generate_forms():
    text = (ROOT / "rdspan" / "seed.py").read_text(encoding="utf-8")
    assert "load_paradigms" in text
    for banned in ("conjugate", "openai", "anthropic", "llm", "stem +"):
        assert banned not in text.lower()


def test_seed_drops_removed_phrases(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "rdspan.db"))
    conn = connect()
    migrate(conn)
    conn.execute(
        """
        INSERT INTO phrases (id, title, text, tts_text, source, license, verified_at, sort_order)
        VALUES ('p01', 'old', 'Yo soy estudiante.', 'Yo soy estudiante.', 'x', 'CC0-1.0', '2026-09-11', 1)
        """
    )
    conn.commit()
    stats = seed(conn)
    assert stats["phrases"] == 0
    assert conn.execute("SELECT COUNT(*) FROM phrases").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM paradigms").fetchone()[0] == len(LEMMAS) * len(TENSES)
    conn.close()
