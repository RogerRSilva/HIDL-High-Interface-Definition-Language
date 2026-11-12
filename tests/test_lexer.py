import pytest

from hidl.errors import ContractError
from hidl.lexer import COLON, EOF, IDENT, LBRACE, RBRACE, SEMI, tokenize


def kinds(src):
    return [t.kind for t in tokenize(src)]


def test_tokens_basicos():
    assert kinds("packet P { a: uint8; }") == [IDENT, IDENT, LBRACE, IDENT, COLON, IDENT, SEMI, RBRACE, EOF]


def test_posicao_linha_coluna():
    toks = tokenize("packet P {\n    id: uint16;\n}")
    campo = next(t for t in toks if t.text == "id")
    assert (campo.line, campo.column) == (2, 5)


def test_comentarios_sao_ignorados():
    assert kinds("// c1\npacket # c2\nP") == [IDENT, IDENT, EOF]


def test_identificadores_com_underscore_e_digitos():
    toks = tokenize("_x1 abc_9")
    assert [t.text for t in toks[:2]] == ["_x1", "abc_9"]


def test_vazio_so_tem_eof():
    assert kinds("") == [EOF] and kinds("  \n\t// só comentário") == [EOF]


def test_caracteres_invalidos_sao_coletados_juntos():
    with pytest.raises(ContractError) as e:
        tokenize("packet P { a: uint8; } @ $")
    assert [(d.line, d.column) for d in e.value.diagnostics] == [(1, 24), (1, 26)]
    assert "caractere inesperado" in e.value.diagnostics[0].message


def test_numero_no_inicio_de_identificador_e_invalido():
    with pytest.raises(ContractError):
        tokenize("9abc")
