#!/usr/bin/env python3
"""Write data/paradigms.json from curated finite tables (grammar ch. 16).

This is an authoring helper. Runtime seed copies JSON into SQLite and
does not inflect verbs. Forms are grammatical facts; citations point at
Butt, Benjamin and Moreira Rodríguez (2019), ch. 16.

Regular models are 16.3. Every other lemma is from the 16.12 list
(or a 16.11 model named there), conjugated like the cited model.
Obsolete defectives in parentheses are omitted.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "paradigms.json"

SOURCE = (
    "Butt, Benjamin and Moreira Rodríguez, "
    "A New Reference Grammar of Modern Spanish, 6th ed. (2019), "
    "chapter 16 (forms of Spanish verbs). Curated finite tables in rdspan."
)
LICENSE = "CC0-1.0"
VERIFIED_AT = "2026-09-11"
PRONOUNS = ("yo", "tú", "él", "nosotros", "vosotros", "ellos")
SLOTS = ("1s", "2s", "3s", "1p", "2p", "3p")
TENSES = [
    ("presente", "indicativo"),
    ("imperfecto", "indicativo"),
    ("pretérito", "indicativo"),
    ("futuro", "indicativo"),
    ("condicional", "indicativo"),
    ("presente", "subjuntivo"),
    ("imperfecto", "subjuntivo"),
]
FUT = ("é", "ás", "á", "emos", "éis", "án")
COND = ("ía", "ías", "ía", "íamos", "íais", "ían")
STRONG = (0, 1, 2, 5)

# Regular models first (16.3), then 16.12 irregulars.
REGULARS = ("hablar", "comer", "vivir")


def _tables(pres: str, impf: str, pret: str, fut: str, cond: str, subj: str, imps: str):
    return [
        ("presente", "indicativo", pres),
        ("imperfecto", "indicativo", impf),
        ("pretérito", "indicativo", pret),
        ("futuro", "indicativo", fut),
        ("condicional", "indicativo", cond),
        ("presente", "subjuntivo", subj),
        ("imperfecto", "subjuntivo", imps),
    ]


def _join(parts: list[str]) -> str:
    return " ".join(parts)


def _future(stem: str) -> str:
    return _join(stem + e for e in FUT)


def _conditional(stem: str) -> str:
    return _join(stem + e for e in COND)


def _replace_last(stem: str, old: str, new: str) -> str:
    i = stem.rfind(old)
    if i < 0:
        raise ValueError(f"no {old} in {stem}")
    return stem[:i] + new + stem[i + 1 :]


def _ue(stem: str) -> str:
    i = stem.rfind("o")
    if i < 0:
        raise ValueError(f"expected o in {stem}")
    if i and stem[i - 1] == "g":
        out = stem[: i - 1] + "güe" + stem[i + 1 :]
    else:
        out = stem[:i] + "ue" + stem[i + 1 :]
    if out.startswith("ue"):
        return "h" + out
    return out


def _ie(stem: str) -> str:
    out = _replace_last(stem, "e", "ie")
    if out.startswith("ie"):
        return "y" + out[1:]
    return out


def _e2i(stem: str) -> str:
    return _replace_last(stem, "e", "i")


def _o2u(stem: str) -> str:
    return _replace_last(stem, "o", "u")


def _i2ie(stem: str) -> str:
    return _replace_last(stem, "i", "ie")


def _u2ue(stem: str) -> str:
    return _replace_last(stem, "u", "ue")


def add(stem: str, ending: str, kind: str = "") -> str:
    if not ending:
        return stem
    first = ending[0]
    if first in "eé":
        if stem.endswith("z"):
            stem = stem[:-1] + "c"
        elif stem.endswith("g") and kind not in ("gir", "guir", "cocer"):
            stem = stem + "u"
        elif (
            stem.endswith("c")
            and not stem.endswith("zc")
            and kind not in ("cocer", "gir", "guir")
        ):
            stem = stem[:-1] + "qu"
    elif first in "oaáó":
        if kind == "guir" and stem.endswith("gu"):
            stem = stem[:-1]
        elif kind == "gir" and stem.endswith("g"):
            stem = stem[:-1] + "j"
        elif kind == "cocer" and stem.endswith("c"):
            stem = stem[:-1] + "z"
    return stem + ending


def _palatal(form: str) -> str:
    return (
        form.replace("ñió", "ñó")
        .replace("llió", "lló")
        .replace("ñie", "ñe")
        .replace("llie", "lle")
    )


def _map_tables(rows: list[tuple[str, str, str]], fn) -> list[tuple[str, str, str]]:
    out = []
    for tense, mood, forms in rows:
        out.append((tense, mood, _join(fn(w) for w in forms.split())))
    return out


def _mix(strong: str, weak: str, ends: list[str], kind: str, strong_slots=STRONG) -> str:
    parts = []
    for i, end in enumerate(ends):
        stem = strong if i in strong_slots else weak
        parts.append(add(stem, end, kind))
    return _join(parts)


def _all(stem: str, ends: list[str], kind: str = "") -> str:
    return _join(add(stem, e, kind) for e in ends)


def conj_ar(lemma: str, strong: str | None = None, kind: str = "") -> list:
    weak = lemma[:-2]
    s = strong or weak
    return _tables(
        _mix(s, weak, ["o", "as", "a", "amos", "áis", "an"], kind),
        _all(weak, ["aba", "abas", "aba", "ábamos", "abais", "aban"], kind),
        _all(weak, ["é", "aste", "ó", "amos", "asteis", "aron"], kind),
        _future(lemma),
        _conditional(lemma),
        _mix(s, weak, ["e", "es", "e", "emos", "éis", "en"], kind),
        _all(weak, ["ara", "aras", "ara", "áramos", "arais", "aran"], kind),
    )


def conj_er(lemma: str, strong: str | None = None, kind: str = "") -> list:
    weak = lemma[:-2]
    s = strong or weak
    return _tables(
        _mix(s, weak, ["o", "es", "e", "emos", "éis", "en"], kind),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"], kind),
        _all(weak, ["í", "iste", "ió", "imos", "isteis", "ieron"], kind),
        _future(lemma),
        _conditional(lemma),
        _mix(s, weak, ["a", "as", "a", "amos", "áis", "an"], kind),
        _all(weak, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"], kind),
    )


def conj_ir(lemma: str, strong: str | None = None, kind: str = "") -> list:
    weak = lemma[:-2]
    s = strong or weak
    return _tables(
        _mix(s, weak, ["o", "es", "e", "imos", "ís", "en"], kind),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"], kind),
        _all(weak, ["í", "iste", "ió", "imos", "isteis", "ieron"], kind),
        _future(lemma),
        _conditional(lemma),
        _mix(s, weak, ["a", "as", "a", "amos", "áis", "an"], kind),
        _all(weak, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"], kind),
    )


def conj_pedir(lemma: str, kind: str = "") -> list:
    weak = lemma[:-2]
    s = _e2i(weak)
    pret = [
        add(weak, "í", kind),
        add(weak, "iste", kind),
        add(s, "ió", kind),
        add(weak, "imos", kind),
        add(weak, "isteis", kind),
        add(s, "ieron", kind),
    ]
    return _tables(
        _mix(s, weak, ["o", "es", "e", "imos", "ís", "en"], kind),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"], kind),
        _join(pret),
        _future(lemma),
        _conditional(lemma),
        _all(s, ["a", "as", "a", "amos", "áis", "an"], kind),
        _all(s, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"], kind),
    )


def conj_sentir(lemma: str) -> list:
    weak = lemma[:-2]
    ie = _ie(weak)
    i_st = _e2i(weak)
    return _tables(
        _mix(ie, weak, ["o", "es", "e", "imos", "ís", "en"], ""),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"]),
        _join(
            [
                weak + "í",
                weak + "iste",
                i_st + "ió",
                weak + "imos",
                weak + "isteis",
                i_st + "ieron",
            ]
        ),
        _future(lemma),
        _conditional(lemma),
        _mix(ie, i_st, ["a", "as", "a", "amos", "áis", "an"], ""),
        _all(i_st, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"]),
    )


def conj_dormir(lemma: str) -> list:
    weak = lemma[:-2]
    ue = _ue(weak)
    u_st = _o2u(weak)
    return _tables(
        _mix(ue, weak, ["o", "es", "e", "imos", "ís", "en"], ""),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"]),
        _join(
            [
                weak + "í",
                weak + "iste",
                u_st + "ió",
                weak + "imos",
                weak + "isteis",
                u_st + "ieron",
            ]
        ),
        _future(lemma),
        _conditional(lemma),
        _mix(ue, u_st, ["a", "as", "a", "amos", "áis", "an"], ""),
        _all(u_st, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"]),
    )


def conj_jugar(lemma: str) -> list:
    return conj_ar(lemma, strong=_u2ue(lemma[:-2]))


def conj_cer(lemma: str) -> list:
    weak = lemma[:-2]
    zc = weak[:-1] + "zc"
    return _tables(
        _join([zc + "o", weak + "es", weak + "e", weak + "emos", weak + "éis", weak + "en"]),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"]),
        _all(weak, ["í", "iste", "ió", "imos", "isteis", "ieron"]),
        _future(lemma),
        _conditional(lemma),
        _all(zc, ["a", "as", "a", "amos", "áis", "an"]),
        _all(weak, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"]),
    )


def conj_lucir(lemma: str) -> list:
    weak = lemma[:-2]
    zc = weak[:-1] + "zc"
    return _tables(
        _join([zc + "o", weak + "es", weak + "e", weak + "imos", weak + "ís", weak + "en"]),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"]),
        _all(weak, ["í", "iste", "ió", "imos", "isteis", "ieron"]),
        _future(lemma),
        _conditional(lemma),
        _all(zc, ["a", "as", "a", "amos", "áis", "an"]),
        _all(weak, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"]),
    )


def conj_producir(lemma: str) -> list:
    weak = lemma[:-2]
    zc = weak[:-1] + "zc"
    j = lemma[:-3] + "j"
    return _tables(
        _join([zc + "o", weak + "es", weak + "e", weak + "imos", weak + "ís", weak + "en"]),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"]),
        _join([j + "e", j + "iste", j + "o", j + "imos", j + "isteis", j + "eron"]),
        _future(lemma),
        _conditional(lemma),
        _all(zc, ["a", "as", "a", "amos", "áis", "an"]),
        _join([j + "era", j + "eras", j + "era", j + "éramos", j + "erais", j + "eran"]),
    )


def conj_construir(lemma: str) -> list:
    if lemma == "argüir":
        return _tables(
            "arguyo arguyes arguye argüimos argüís arguyen",
            "argüía argüías argüía argüíamos argüíais argüían",
            "argüí argüiste arguyó argüimos argüisteis arguyeron",
            _future("argüir"),
            _conditional("argüir"),
            "arguya arguyas arguya arguyamos arguyáis arguyan",
            "arguyera arguyeras arguyera arguyéramos arguyerais arguyeran",
        )
    if lemma == "rehuir":
        return _tables(
            "rehúyo rehúyes rehúye rehuimos rehuís rehúyen",
            "rehuía rehuías rehuía rehuíamos rehuíais rehuían",
            "rehuí rehuiste rehuyó rehuimos rehuisteis rehuyeron",
            _future("rehuir"),
            _conditional("rehuir"),
            "rehúya rehúyas rehúya rehuamos rehuáis rehúyan",
            "rehuyera rehuyeras rehuyera rehuyéramos rehuyerais rehuyeran",
        )
    stem = lemma[:-2]
    pres = _join(
        [stem + "yo", stem + "yes", stem + "ye", stem + "imos", stem + "ís", stem + "yen"]
    )
    impf = _all(stem, ["ía", "ías", "ía", "íamos", "íais", "ían"])
    pret = _join(
        [
            stem + "í",
            stem + "iste",
            stem + "yó",
            stem + "imos",
            stem + "isteis",
            stem + "yeron",
        ]
    )
    subj = _all(stem, ["ya", "yas", "ya", "yamos", "yáis", "yan"])
    imps = _all(stem, ["yera", "yeras", "yera", "yéramos", "yerais", "yeran"])
    rows = _tables(pres, impf, pret, _future(lemma), _conditional(lemma), subj, imps)
    if lemma == "huir":
        rows = _map_tables(rows, lambda w: {"huís": "huis", "huí": "hui"}.get(w, w))
    if lemma == "fluir":
        rows = _map_tables(rows, lambda w: {"fluís": "fluis", "fluí": "flui"}.get(w, w))
    return rows


def conj_poseer(lemma: str) -> list:
    weak = lemma[:-2]
    return _tables(
        _all(weak, ["o", "es", "e", "emos", "éis", "en"]),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"]),
        _join(
            [
                weak + "í",
                weak + "íste",
                weak + "yó",
                weak + "ímos",
                weak + "ísteis",
                weak + "yeron",
            ]
        ),
        _future(lemma),
        _conditional(lemma),
        _all(weak, ["a", "as", "a", "amos", "áis", "an"]),
        _all(weak, ["yera", "yeras", "yera", "yéramos", "yerais", "yeran"]),
    )


def conj_reir(lemma: str) -> list:
    prefix = lemma[:-3]
    def p(rest: str) -> str:
        return prefix + rest

    pret3 = p("io")
    if pret3 not in ("rio", "frio"):
        pret3 = pret3[:-2] + "ió"
    return _tables(
        _join([p("ío"), p("íes"), p("íe"), p("eímos"), p("eís"), p("íen")]),
        _join([p("eía"), p("eías"), p("eía"), p("eíamos"), p("eíais"), p("eían")]),
        _join([p("eí"), p("eíste"), pret3, p("eímos"), p("eísteis"), p("ieron")]),
        _future(lemma),
        _conditional(lemma),
        _join([p("ía"), p("ías"), p("ía"), p("iamos"), p("iais"), p("ían")]),
        _join([p("iera"), p("ieras"), p("iera"), p("iéramos"), p("ierais"), p("ieran")]),
    )


def conj_adquirir(lemma: str) -> list:
    weak = lemma[:-2]
    s = _i2ie(weak)
    return _tables(
        _mix(s, weak, ["o", "es", "e", "imos", "ís", "en"], ""),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"]),
        _all(weak, ["í", "iste", "ió", "imos", "isteis", "ieron"]),
        _future(lemma),
        _conditional(lemma),
        _mix(s, weak, ["a", "as", "a", "amos", "áis", "an"], ""),
        _all(weak, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"]),
    )


def conj_discernir(lemma: str) -> list:
    weak = lemma[:-2]
    s = _ie(weak)
    return _tables(
        _mix(s, weak, ["o", "es", "e", "imos", "ís", "en"], ""),
        _all(weak, ["ía", "ías", "ía", "íamos", "íais", "ían"]),
        _all(weak, ["í", "iste", "ió", "imos", "isteis", "ieron"]),
        _future(lemma),
        _conditional(lemma),
        _mix(s, weak, ["a", "as", "a", "amos", "áis", "an"], ""),
        _all(weak, ["iera", "ieras", "iera", "iéramos", "ierais", "ieran"]),
    )


def _pal_rows(rows: list) -> list:
    return _map_tables(rows, _palatal)


UNIQUE = {
    "andar": _tables(
        "ando andas anda andamos andáis andan",
        "andaba andabas andaba andábamos andabais andaban",
        "anduve anduviste anduvo anduvimos anduvisteis anduvieron",
        _future("andar"),
        _conditional("andar"),
        "ande andes ande andemos andéis anden",
        "anduviera anduvieras anduviera anduviéramos anduvierais anduvieran",
    ),
    "caber": _tables(
        "quepo cabes cabe cabemos cabéis caben",
        "cabía cabías cabía cabíamos cabíais cabían",
        "cupe cupiste cupo cupimos cupisteis cupieron",
        _future("cabr"),
        _conditional("cabr"),
        "quepa quepas quepa quepamos quepáis quepan",
        "cupiera cupieras cupiera cupiéramos cupierais cupieran",
    ),
    "caer": _tables(
        "caigo caes cae caemos caéis caen",
        "caía caías caía caíamos caíais caían",
        "caí caíste cayó caímos caísteis cayeron",
        _future("caer"),
        _conditional("caer"),
        "caiga caigas caiga caigamos caigáis caigan",
        "cayera cayeras cayera cayéramos cayerais cayeran",
    ),
    "dar": _tables(
        "doy das da damos dais dan",
        "daba dabas daba dábamos dabais daban",
        "di diste dio dimos disteis dieron",
        _future("dar"),
        _conditional("dar"),
        "dé des dé demos deis den",
        "diera dieras diera diéramos dierais dieran",
    ),
    "decir": _tables(
        "digo dices dice decimos decís dicen",
        "decía decías decía decíamos decíais decían",
        "dije dijiste dijo dijimos dijisteis dijeron",
        _future("dir"),
        _conditional("dir"),
        "diga digas diga digamos digáis digan",
        "dijera dijeras dijera dijéramos dijerais dijeran",
    ),
    "estar": _tables(
        "estoy estás está estamos estáis están",
        "estaba estabas estaba estábamos estabais estaban",
        "estuve estuviste estuvo estuvimos estuvisteis estuvieron",
        _future("estar"),
        _conditional("estar"),
        "esté estés esté estemos estéis estén",
        "estuviera estuvieras estuviera estuviéramos estuvierais estuvieran",
    ),
    "haber": _tables(
        "he has ha hemos habéis han",
        "había habías había habíamos habíais habían",
        "hube hubiste hubo hubimos hubisteis hubieron",
        _future("habr"),
        _conditional("habr"),
        "haya hayas haya hayamos hayáis hayan",
        "hubiera hubieras hubiera hubiéramos hubierais hubieran",
    ),
    "hacer": _tables(
        "hago haces hace hacemos hacéis hacen",
        "hacía hacías hacía hacíamos hacíais hacían",
        "hice hiciste hizo hicimos hicisteis hicieron",
        _future("har"),
        _conditional("har"),
        "haga hagas haga hagamos hagáis hagan",
        "hiciera hicieras hiciera hiciéramos hicierais hicieran",
    ),
    "ir": _tables(
        "voy vas va vamos vais van",
        "iba ibas iba íbamos ibais iban",
        "fui fuiste fue fuimos fuisteis fueron",
        _future("ir"),
        _conditional("ir"),
        "vaya vayas vaya vayamos vayáis vayan",
        "fuera fueras fuera fuéramos fuerais fueran",
    ),
    "oír": _tables(
        "oigo oyes oye oímos oís oyen",
        "oía oías oía oíamos oíais oían",
        "oí oíste oyó oímos oísteis oyeron",
        _future("oír"),
        _conditional("oír"),
        "oiga oigas oiga oigamos oigáis oigan",
        "oyera oyeras oyera oyéramos oyerais oyeran",
    ),
    "poder": _tables(
        "puedo puedes puede podemos podéis pueden",
        "podía podías podía podíamos podíais podían",
        "pude pudiste pudo pudimos pudisteis pudieron",
        _future("podr"),
        _conditional("podr"),
        "pueda puedas pueda podamos podáis puedan",
        "pudiera pudieras pudiera pudiéramos pudierais pudieran",
    ),
    "poner": _tables(
        "pongo pones pone ponemos ponéis ponen",
        "ponía ponías ponía poníamos poníais ponían",
        "puse pusiste puso pusimos pusisteis pusieron",
        _future("pondr"),
        _conditional("pondr"),
        "ponga pongas ponga pongamos pongáis pongan",
        "pusiera pusieras pusiera pusiéramos pusierais pusieran",
    ),
    "querer": _tables(
        "quiero quieres quiere queremos queréis quieren",
        "quería querías quería queríamos queríais querían",
        "quise quisiste quiso quisimos quisisteis quisieron",
        _future("querr"),
        _conditional("querr"),
        "quiera quieras quiera queramos queráis quieran",
        "quisiera quisieras quisiera quisiéramos quisierais quisieran",
    ),
    "saber": _tables(
        "sé sabes sabe sabemos sabéis saben",
        "sabía sabías sabía sabíamos sabíais sabían",
        "supe supiste supo supimos supisteis supieron",
        _future("sabr"),
        _conditional("sabr"),
        "sepa sepas sepa sepamos sepáis sepan",
        "supiera supieras supiera supiéramos supierais supieran",
    ),
    "salir": _tables(
        "salgo sales sale salimos salís salen",
        "salía salías salía salíamos salíais salían",
        "salí saliste salió salimos salisteis salieron",
        _future("saldr"),
        _conditional("saldr"),
        "salga salgas salga salgamos salgáis salgan",
        "saliera salieras saliera saliéramos salierais salieran",
    ),
    "ser": _tables(
        "soy eres es somos sois son",
        "era eras era éramos erais eran",
        "fui fuiste fue fuimos fuisteis fueron",
        _future("ser"),
        _conditional("ser"),
        "sea seas sea seamos seáis sean",
        "fuera fueras fuera fuéramos fuerais fueran",
    ),
    "tener": _tables(
        "tengo tienes tiene tenemos tenéis tienen",
        "tenía tenías tenía teníamos teníais tenían",
        "tuve tuviste tuvo tuvimos tuvisteis tuvieron",
        _future("tendr"),
        _conditional("tendr"),
        "tenga tengas tenga tengamos tengáis tengan",
        "tuviera tuvieras tuviera tuviéramos tuvierais tuvieran",
    ),
    "traer": _tables(
        "traigo traes trae traemos traéis traen",
        "traía traías traía traíamos traíais traían",
        "traje trajiste trajo trajimos trajisteis trajeron",
        _future("traer"),
        _conditional("traer"),
        "traiga traigas traiga traigamos traigáis traigan",
        "trajera trajeras trajera trajéramos trajerais trajeran",
    ),
    "valer": _tables(
        "valgo vales vale valemos valéis valen",
        "valía valías valía valíamos valíais valían",
        "valí valiste valió valimos valisteis valieron",
        _future("valdr"),
        _conditional("valdr"),
        "valga valgas valga valgamos valgáis valgan",
        "valiera valieras valiera valiéramos valierais valieran",
    ),
    "venir": _tables(
        "vengo vienes viene venimos venís vienen",
        "venía venías venía veníamos veníais venían",
        "vine viniste vino vinimos vinisteis vinieron",
        _future("vendr"),
        _conditional("vendr"),
        "venga vengas venga vengamos vengáis vengan",
        "viniera vinieras viniera viniéramos vinierais vinieran",
    ),
    "ver": _tables(
        "veo ves ve vemos veis ven",
        "veía veías veía veíamos veíais veían",
        "vi viste vio vimos visteis vieron",
        _future("ver"),
        _conditional("ver"),
        "vea veas vea veamos veáis vean",
        "viera vieras viera viéramos vierais vieran",
    ),
}

VER_ACCENT = {
    "ves": "vés",
    "ve": "vé",
    "veis": "véis",
    "ven": "vén",
    "vi": "ví",
    "vio": "vió",
}


def _prefix_root(lemma: str, root: str, *, ver: bool = False, drop_h: bool = False) -> list:
    prefix = lemma[: -len(root)]
    def fn(form: str) -> str:
        if drop_h and form.startswith("h"):
            return prefix + form[1:]
        if ver:
            return prefix + VER_ACCENT.get(form, form)
        return prefix + form

    return _map_tables(UNIQUE[root], fn)


def conj_decir_family(lemma: str, future_mode: str) -> list:
    prefix = lemma[:-5]
    rows = _prefix_root(lemma, "decir")
    if future_mode == "regular":
        fut, cond = _future(lemma), _conditional(lemma)
        out = []
        for tense, mood, forms in rows:
            if tense == "futuro":
                out.append((tense, mood, fut))
            elif tense == "condicional":
                out.append((tense, mood, cond))
            else:
                out.append((tense, mood, forms))
        return out
    return rows


def inflect(lemma: str, family: str) -> list:
    if lemma in UNIQUE:
        return UNIQUE[lemma]
    if family == "ar":
        return conj_ar(lemma)
    if family == "er":
        return conj_er(lemma)
    if family == "ir":
        return conj_ir(lemma)
    if family == "contar":
        return conj_ar(lemma, strong=_ue(lemma[:-2]))
    if family == "cerrar":
        return conj_ar(lemma, strong=_ie(lemma[:-2]))
    if family == "mover":
        return conj_er(lemma, strong=_ue(lemma[:-2]))
    if family == "perder":
        return conj_er(lemma, strong=_ie(lemma[:-2]))
    if family == "pedir":
        return conj_pedir(lemma)
    if family == "gir":
        return conj_pedir(lemma, kind="gir")
    if family == "guir":
        return conj_pedir(lemma, kind="guir")
    if family == "sentir":
        return conj_sentir(lemma)
    if family == "dormir":
        return conj_dormir(lemma)
    if family == "morir":
        return conj_dormir(lemma)
    if family == "jugar":
        return conj_jugar(lemma)
    if family == "construir":
        return conj_construir(lemma)
    if family == "cer":
        return conj_cer(lemma)
    if family == "lucir":
        return conj_lucir(lemma)
    if family == "producir":
        return conj_producir(lemma)
    if family == "cocer":
        return conj_er(lemma, strong=_ue(lemma[:-2]), kind="cocer")
    if family == "oler":
        return conj_er(lemma, strong=_ue(lemma[:-2]))
    if family == "poseer":
        return conj_poseer(lemma)
    if family == "reir":
        return conj_reir(lemma)
    if family == "renir":
        return _pal_rows(conj_pedir(lemma))
    if family == "adquirir":
        return conj_adquirir(lemma)
    if family == "discernir":
        return conj_discernir(lemma)
    if family == "errar":
        return conj_ar(lemma, strong=_ie(lemma[:-2]))
    if family == "erguir":
        return _tables(
            "yergo yergues yergue erguimos erguís yerguen",
            "erguía erguías erguía erguíamos erguíais erguían",
            "erguí erguiste irguió erguimos erguisteis irguieron",
            _future("erguir"),
            _conditional("erguir"),
            "yerga yergas yerga yergamos yergáis yergan",
            "irguiera irguieras irguiera irguiéramos irguierais irguieran",
        )
    if family == "asir":
        return _tables(
            "asgo ases ase asimos asís asen",
            "asía asías asía asíamos asíais asían",
            "así asiste asió asimos asisteis asieron",
            _future("asir"),
            _conditional("asir"),
            "asga asgas asga asgamos asgáis asgan",
            "asiera asieras asiera asiéramos asierais asieran",
        )
    if family == "roer":
        rows = _tables(
            "roo roes roe roemos roéis roen",
            "roía roías roía roíamos roíais roían",
            "roí roíste royó roímos roísteis royeron",
            _future("roer"),
            _conditional("roer"),
            "roa roas roa roamos roáis roan",
            "royera royeras royera royéramos royerais royeran",
        )
        if lemma == "roer":
            return rows
        prefix = lemma[: -len("roer")]
        return _map_tables(rows, lambda w: prefix + w)
    if family == "yacer":
        return conj_cer(lemma)
    if family == "n_er":
        return _pal_rows(conj_er(lemma))
    if family == "n_ir":
        return _pal_rows(conj_ir(lemma))
    if family == "ll_ir":
        return _pal_rows(conj_ir(lemma))
    if family == "maldecir":
        return conj_decir_family(lemma, "regular")
    if family == "predecir":
        return conj_decir_family(lemma, "regular")
    if family == "contradecir":
        return conj_decir_family(lemma, "dir")
    if family == "satisfacer":
        return _map_tables(UNIQUE["hacer"], lambda w: "satisf" + w[1:] if w.startswith("h") else "satisf" + w)
    if family in UNIQUE:
        if lemma == family:
            return UNIQUE[family]
        if lemma == "raer":
            return _map_tables(UNIQUE["caer"], lambda w: "r" + w[1:] if w.startswith("c") else w)
        if family == "ver":
            return _prefix_root(lemma, "ver", ver=True)
        if family == "oír":
            return _prefix_root(lemma, "oír")
        return _prefix_root(lemma, family)
    raise ValueError(f"unknown family {family} for {lemma}")


# 16.12 headwords, se-stripped, obsolete parentheticals omitted.
CATALOG = """
abastecer cer
abolir ir
aborrecer cer
abrir ir
absolver mover
abstener tener
abstraer traer
acaecer cer
acertar cerrar
acontecer cer
acordar contar
acostar contar
acrecentar cerrar
adherir sentir
adolecer cer
adormecer cer
adquirir adquirir
aducir producir
advertir sentir
agradecer cer
agredir ir
alentar cerrar
almorzar contar
amanecer cer
amoblar contar
andar andar
anochecer cer
anteponer poner
apacentar cerrar
aparecer cer
apetecer cer
apostar contar
apretar cerrar
aprobar contar
argüir construir
arrendar cerrar
arrepentir sentir
ascender perder
asentar cerrar
asentir sentir
asir asir
asolar contar
atañer n_er
atender perder
atener tener
aterrar cerrar
atraer traer
atravesar cerrar
atribuir construir
avenir venir
aventar cerrar
avergonzar contar
bendecir maldecir
bruñir n_ir
bullir ll_ir
caber caber
caer caer
calentar cerrar
carecer cer
cegar cerrar
ceñir renir
cerner perder
cernir discernir
cerrar cerrar
circunscribir ir
cocer cocer
colar contar
colegir gir
colgar contar
comenzar cerrar
compadecer cer
comparecer cer
competir pedir
complacer cer
componer poner
comprobar contar
concebir pedir
concernir discernir
concertar cerrar
concluir construir
concordar contar
condescender perder
condoler mover
conducir producir
conferir sentir
confesar cerrar
confluir construir
conmover mover
conocer cer
conseguir guir
consentir sentir
consolar contar
consonar contar
constituir construir
constreñir renir
construir construir
contar contar
contender perder
contener tener
contradecir contradecir
contraer traer
contrahacer hacer
contraponer poner
contravenir venir
contribuir construir
controvertir sentir
convalecer cer
convenir venir
convertir sentir
corregir gir
corroer roer
costar contar
crecer cer
creer poseer
cubrir ir
dar dar
decaer caer
decir decir
decrecer cer
deducir producir
defender perder
deferir sentir
degollar contar
demoler mover
demostrar contar
denegar cerrar
denostar contar
deponer poner
derretir pedir
derrocar ar
desacertar cerrar
desacordar contar
desagradecer cer
desalentar cerrar
desandar andar
desaparecer cer
desapretar cerrar
desaprobar contar
desasosegar cerrar
desatender perder
desavenir venir
descender perder
desceñir renir
descolgar contar
descollar contar
descomponer poner
desconcertar cerrar
desconocer cer
desconsolar contar
descontar contar
desconvenir venir
describir ir
descubrir ir
desdecir decir
desempedrar cerrar
desengrosar contar
desentender perder
desenterrar cerrar
desenvolver mover
desfallecer cer
desgobernar cerrar
deshacer hacer
deshelar cerrar
desherrar cerrar
desleír reir
deslucir lucir
desmembrar cerrar
desmentir sentir
desmerecer cer
desobedecer cer
desoír oír
desollar contar
despedir pedir
despedrar cerrar
despertar cerrar
despezar cerrar
desplacer cer
desplegar cerrar
despoblar contar
desproveer poseer
desteñir renir
desterrar cerrar
destituir construir
destruir construir
desvanecer cer
desvergonzar contar
detener tener
detraer traer
devenir venir
devolver mover
diferir sentir
digerir sentir
diluir construir
discernir discernir
disentir sentir
disminuir construir
disolver mover
disponer poner
distender perder
distraer traer
distribuir construir
divertir sentir
doler mover
dormir dormir
elegir gir
embebecer cer
embellecer cer
embestir pedir
embravecer cer
embrutecer cer
empedrar cerrar
empequeñecer cer
empezar cerrar
empobrecer cer
enaltecer cer
enardecer cer
encanecer cer
encarecer cer
encender perder
encerrar cerrar
encomendar cerrar
encontrar contar
encubrir ir
endurecer cer
enflaquecer cer
enfurecer cer
engrandecer cer
engreír reir
engrosar contar
engullir ll_ir
enloquecer cer
enmendar cerrar
enmohecer cer
enmudecer cer
ennegrecer cer
ennoblecer cer
enorgullecer cer
enriquecer cer
enronquecer cer
ensangrentar cerrar
ensoberbecer cer
ensordecer cer
entender perder
enternecer cer
enterrar cerrar
entreabrir ir
entredecir decir
entreoír oír
entretener tener
entrever ver
entristecer cer
entumecer cer
envanecer cer
envejecer cer
envilecer cer
envolver mover
equivaler valer
erguir erguir
errar errar
escabullir ll_ir
escarmentar cerrar
escarnecer cer
escocer cocer
escribir ir
esforzar contar
establecer cer
estar estar
estremecer cer
estreñir renir
excluir construir
expedir pedir
exponer poner
extender perder
extraer traer
fallecer cer
favorecer cer
florecer cer
fluir construir
fortalecer cer
forzar contar
fregar cerrar
freír reir
gemir pedir
gobernar cerrar
gruñir n_ir
guarecer cer
guarnecer cer
haber haber
hacer hacer
heder perder
helar cerrar
henchir pedir
hender perder
hendir discernir
herir sentir
herrar cerrar
hervir sentir
holgar contar
hollar contar
huir construir
humedecer cer
impedir pedir
imponer poner
incensar cerrar
incluir construir
indisponer poner
inducir producir
inferir sentir
influir construir
ingerir sentir
injerir sentir
inquirir adquirir
inscribir ir
instituir construir
instruir construir
interferir sentir
interponer poner
intervenir venir
introducir producir
intuir construir
invernar cerrar
invertir sentir
investir pedir
ir ir
jugar jugar
languidecer cer
leer poseer
llover mover
lucir lucir
maldecir maldecir
manifestar cerrar
mantener tener
medir pedir
mentar cerrar
mentir sentir
merecer cer
merendar cerrar
moler mover
morder mover
morir morir
mostrar contar
mover mover
mullir ll_ir
nacer cer
negar cerrar
nevar cerrar
obedecer cer
obscurecer cer
obstruir construir
obtener tener
ofrecer cer
oír oír
oler oler
oponer poner
oscurecer cer
pacer cer
padecer cer
palidecer cer
parecer cer
pedir pedir
pensar cerrar
perder perder
perecer cer
permanecer cer
perseguir guir
pertenecer cer
pervertir sentir
placer cer
plegar cerrar
poblar contar
poder poder
poner poner
poseer poseer
posponer poner
predecir predecir
predisponer poner
preferir sentir
prescribir ir
presuponer poner
prevalecer cer
prevaler valer
prevenir venir
prever ver
probar contar
producir producir
proferir sentir
promover mover
proponer poner
proseguir guir
prostituir construir
proveer poseer
provenir venir
quebrar cerrar
querer querer
raer caer
reaparecer cer
reblandecer cer
recaer caer
recluir construir
recocer cocer
recomendar cerrar
reconocer cer
reconvenir venir
recordar contar
recostar contar
reducir producir
reelegir gir
referir sentir
reforzar contar
refregar cerrar
regar cerrar
regimentar cerrar
regir gir
rehacer hacer
rehuir construir
reír reir
rejuvenecer cer
remendar cerrar
remorder mover
remover mover
rendir pedir
renegar cerrar
renovar contar
reñir renir
repetir pedir
replegar cerrar
repoblar contar
reponer poner
reprobar contar
reproducir producir
requebrar cerrar
requerir sentir
resentir sentir
resollar contar
resolver mover
resonar contar
resplandecer cer
restablecer cer
restituir construir
restregar cerrar
retemblar cerrar
retener tener
reteñir renir
retorcer cocer
retraer traer
retribuir construir
retrotraer traer
reventar cerrar
reverdecer cer
reverter perder
revestir pedir
revolar contar
revolcar contar
revolver mover
robustecer cer
rodar contar
roer roer
rogar contar
romper er
saber saber
salir salir
satisfacer satisfacer
seducir producir
segar cerrar
seguir guir
sembrar cerrar
sentar cerrar
sentir sentir
ser ser
serrar cerrar
servir pedir
sobrentender perder
sobreponer poner
sobresalir salir
sobrevenir venir
sofreír reir
soldar contar
soler mover
soltar contar
sonar contar
sonreír reir
soñar contar
sosegar cerrar
sostener tener
soterrar cerrar
subarrendar cerrar
subvenir venir
subvertir sentir
sugerir sentir
suponer poner
suscribir ir
sustituir construir
sustraer traer
tañer n_er
temblar cerrar
tender perder
tener tener
tentar cerrar
teñir renir
torcer cocer
tostar contar
traducir producir
traer traer
transcribir ir
transferir sentir
transgredir ir
transponer poner
trascender perder
trasegar cerrar
traslucir lucir
trasponer poner
trastrocar contar
trocar contar
tronar contar
tropezar cerrar
tullir ll_ir
valer valer
venir venir
ver ver
verter perder
vestir pedir
volar contar
volcar contar
volver mover
yacer yacer
zaherir sentir
zambullir ll_ir
"""


def parse_catalog() -> list[tuple[str, str]]:
    rows = []
    seen: set[str] = set()
    for line in CATALOG.strip().splitlines():
        lemma, family = line.split()
        if lemma in seen:
            raise SystemExit(f"duplicate catalog lemma {lemma}")
        seen.add(lemma)
        rows.append((lemma, family))
    return rows


def ending_of(lemma: str) -> str:
    if lemma.endswith("ír"):
        return "ir"
    return lemma[-2:]


def slug(text: str) -> str:
    text = text.replace("ñ", "ny").replace("Ñ", "ny")
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )
    return stripped.lower()


def verb_entries() -> list[tuple[str, str, str, str]]:
    """lemma, family, regularity, ending — regulars first, then 16.12 A–Z."""
    out = [(lemma, lemma[-2:], "regular", lemma[-2:]) for lemma in REGULARS]
    seen = set(REGULARS)
    irregulars = []
    for lemma, family in parse_catalog():
        if lemma in seen:
            continue
        seen.add(lemma)
        irregulars.append((lemma, family, "irregular", ending_of(lemma)))
    irregulars.sort(key=lambda row: (slug(row[0]), row[0]))
    return out + irregulars


def build() -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for index, (lemma, family, regularity, ending) in enumerate(verb_entries()):
        if family in ("ar", "er", "ir") and regularity == "regular":
            tables = inflect(lemma, family)
        else:
            tables = inflect(lemma, family)
        base = 10 + index * 10
        for offset, (tense, mood, forms) in enumerate(tables):
            tokens = forms.split()
            if len(tokens) != 6:
                raise SystemExit(f"{lemma} {tense} {mood} needs 6 forms, got {tokens!r}")
            pid = f"{slug(lemma)}.{slug(tense)}.{mood}"
            if pid in seen:
                raise SystemExit(f"duplicate id {pid}")
            seen.add(pid)
            out.append(
                {
                    "id": pid,
                    "lemma": lemma,
                    "ending": ending,
                    "regularity": regularity,
                    "tense": tense,
                    "mood": mood,
                    "source": SOURCE,
                    "license": LICENSE,
                    "verified_at": VERIFIED_AT,
                    "sort_order": base + offset,
                    "cells": [
                        {"slot": slot, "pronoun": pronoun, "form": form}
                        for slot, pronoun, form in zip(SLOTS, PRONOUNS, tokens, strict=True)
                    ],
                }
            )
    return out


def main() -> None:
    rows = build()
    lemmas = verb_entries()
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} paradigms ({len(lemmas)} verbs) to {OUT}")


if __name__ == "__main__":
    main()
