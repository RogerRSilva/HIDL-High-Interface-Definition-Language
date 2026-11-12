import pytest

from hidl.errors import ContractError
from hidl.parser import parse


def err(src):
    with pytest.raises(ContractError) as e:
        parse(src)
    return e.value.diagnostics[0]


def test_pacote_simples():
    (p,) = parse("packet Telemetria {\n  id: uint16;\n  velocidade: uint32;\n}")
    assert (p.name, p.endian, p.line, p.column) == ("Telemetria", None, 1, 8)
    assert [(f.name, f.type_name, f.line, f.column) for f in p.fields] == [
        ("id", "uint16", 2, 3), ("velocidade", "uint32", 3, 3)]


def test_endian_e_posicao_da_diretiva():
    (p,) = parse("packet S endian little { a: uint8; }")
    assert p.endian == "little" and p.endian_pos == (1, 17)


def test_endian_invalido_passa_pelo_parser():
    (p,) = parse("packet S endian middle { a: uint8; }")
    assert p.endian == "middle"  # quem rejeita é a semântica


def test_varios_pacotes_e_arquivo_vazio():
    assert [p.name for p in parse("packet A { x: bool; }\npacket B { y: bool; }")] == ["A", "B"]
    assert parse("// nada aqui") == []


def test_pacote_sem_campos_e_sintaticamente_valido():
    (p,) = parse("packet Vazio { }")
    assert p.fields == []


def test_campo_com_nome_reservado_chega_na_ast():
    (p,) = parse("packet P { clk: uint8; packet: uint8; }")
    assert [f.name for f in p.fields] == ["clk", "packet"]


@pytest.mark.parametrize("src, trecho, pos", [
    ("pacote P { }",                       "esperava 'packet'",      (1, 1)),
    ("packet { a: uint8; }",               "nome do pacote",         (1, 8)),
    ("packet P a: uint8;",                 "'{'",                    (1, 10)),
    ("packet P { a uint8; }",              "':'",                    (1, 14)),
    ("packet P { a: ; }",                  "tipo do campo",          (1, 15)),
    ("packet P { a: uint8 }",              "';'",                    (1, 21)),
    ("packet P { a: uint8;",               "'}'",                    (1, 21)),
    ("packet P endian { a: uint8; }",      "'big' ou 'little'",      (1, 17)),
])
def test_erros_de_sintaxe(src, trecho, pos):
    d = err(src)
    assert trecho in d.message and (d.line, d.column) == pos


def test_erro_no_fim_do_arquivo_menciona_eof():
    assert "fim do arquivo" in err("packet P {").message
