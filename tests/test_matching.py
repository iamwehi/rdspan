from rdspan.matching import cell_match, token_match, tokens


def test_ignores_punctuation_and_case():
    assert token_match("¿Qué dijiste?", "qué dijiste")
    assert token_match("Yo soy estudiante.", "yo soy estudiante")
    assert tokens("¡Hola, mundo!") == ["hola", "mundo"]
    assert not token_match("¿Qué dijiste?", "que dijiste")


def test_keeps_accents():
    assert not token_match("habló", "hablo")
    assert token_match("hablé", "HABLÉ")


def test_cell_allows_optional_pronoun():
    assert cell_match("hablo", "yo", "hablo")
    assert cell_match("hablo", "yo", "yo hablo")
    assert not cell_match("hablo", "yo", "hablas")
