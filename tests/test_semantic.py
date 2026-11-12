"""Testes isolados da análise semântica (AST → IR).

Constroem a AST diretamente, sem passar pelo parser, para que uma falha aqui
aponte para `semantic.py` e não para a gramática.
"""

import dataclasses

import pytest

from hidl.ast import FieldDecl, PacketDecl
from hidl.errors import ContractError
from hidl.semantic import RESERVED, build_ir


def pkt(name="P", fields=(), endian=None, line=1):
    """Monta um PacketDecl. `fields` = [(nome, tipo), ...]; cada campo ocupa uma linha."""
    fs = [FieldDecl(n, t, line + 1 + i, 5) for i, (n, t) in enumerate(fields)]
    return PacketDecl(name, endian, (line, 10), fs, line, 8)


def errors(*decls) -> list[str]:
    with pytest.raises(ContractError) as e:
        build_ir(list(decls))
    return [d.message for d in e.value.diagnostics]


def one(*decls):
    (p,) = build_ir(list(decls))
    return p


# ------------------------------------------------------------- IR / offsets

def test_offsets_e_tamanho_big_endian():
    p = one(pkt(fields=[("id", "uint16"), ("v", "uint32")]))
    assert [(f.name, f.offset, f.width) for f in p.fields] == [("id", 0, 16), ("v", 16, 32)]
    assert (p.total_bits, p.total_bytes, p.endian) == (48, 6, "big")


def test_offsets_campos_nao_alinhados():
    p = one(pkt(fields=[("a", "bool"), ("b", "uint3"), ("c", "uint4"), ("d", "int12"), ("e", "uint4")]))
    assert [f.offset for f in p.fields] == [0, 1, 4, 8, 20]
    assert p.total_bits == 24


def test_tipos_e_sinal():
    p = one(pkt(fields=[("a", "bool"), ("b", "uint7"), ("c", "int8")]))
    assert [(f.kind, f.width, f.signed, f.type_name) for f in p.fields] == [
        ("bool", 1, False, "bool"), ("uint", 7, False, "uint7"), ("int", 8, True, "int8")]


def test_larguras_limite_aceitas():
    one(pkt(fields=[("a", "uint64")]))
    one(pkt(fields=[("a", "int64")]))
    one(pkt(fields=[("a", "uint1"), ("b", "uint7")]))
    one(pkt(fields=[("a", "int2"), ("b", "uint6")]))


def test_varios_pacotes_independentes():
    a, b = build_ir([pkt("A", [("x", "uint8")]), pkt("B", [("x", "uint16")], endian="little", line=5)])
    assert (a.name, a.endian, b.name, b.endian) == ("A", "big", "B", "little")
    assert b.fields[0].offset == 0  # offsets reiniciam a cada pacote


def test_ir_e_imutavel():
    p = one(pkt(fields=[("a", "uint8")]))
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.name = "outro"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.fields[0].offset = 99  # type: ignore[misc]


# ------------------------------------------------------------------- tipos

@pytest.mark.parametrize("tipo", ["float32", "uint", "int", "Uint8", "uint08", "uint0", "u8", "byte", "uint8x", "bool8"])
def test_tipo_desconhecido(tipo):
    assert any("tipo desconhecido" in m for m in errors(pkt(fields=[("a", tipo)])))


@pytest.mark.parametrize("tipo", ["uint65", "int128", "uint72"])
def test_largura_acima_do_maximo(tipo):
    assert any("excede" in m for m in errors(pkt(fields=[("a", tipo)])))


def test_int1_rejeitado():
    assert any("int1" in m for m in errors(pkt(fields=[("a", "int1"), ("b", "uint7")])))


# --------------------------------------------------------- nomes duplicados

def test_campo_duplicado_aponta_linha_e_coluna():
    with pytest.raises(ContractError) as e:
        build_ir([pkt(fields=[("x", "uint8"), ("x", "uint8")])])
    (d,) = e.value.diagnostics
    assert "já declarado" in d.message and "linha 2" in d.message
    assert (d.line, d.column) == (3, 5)


def test_pacote_duplicado():
    msgs = errors(pkt("A", [("x", "uint8")]), pkt("A", [("y", "uint8")], line=5))
    assert any("pacote 'A' já declarado" in m for m in msgs)


def test_mesmo_nome_de_campo_em_pacotes_diferentes_e_valido():
    build_ir([pkt("A", [("x", "uint8")]), pkt("B", [("x", "uint8")], line=5)])


# ------------------------------------------------------ palavras reservadas

@pytest.mark.parametrize("nome", ["clk", "rst_n", "in_valid", "in_sof", "in_data", "out_valid",   # portas Verilog
                                  "module", "wire", "reg", "begin",                                 # Verilog
                                  "class", "struct", "namespace", "decode", "encode",               # C++ / métodos gerados
                                  "packet", "endian"])                                              # contrato
def test_campo_com_nome_reservado(nome):
    assert any("reservada" in m for m in errors(pkt(fields=[(nome, "uint8")])))


def test_pacote_com_nome_reservado():
    assert any("reservada" in m for m in errors(pkt("class", [("x", "uint8")])))


def test_reservadas_cobrem_todos_os_alvos():
    assert {"packet", "endian", "clk", "out_valid", "module", "class", "decode"} <= RESERVED


# ----------------------------------------------------------------- endianness

def test_endian_padrao_big():
    assert one(pkt(fields=[("a", "uint12"), ("b", "uint4")])).endian == "big"


def test_endian_invalido():
    assert any("endianness inválida 'middle'" in m for m in errors(pkt(fields=[("a", "uint8")], endian="middle")))


def test_endian_invalido_aponta_posicao_da_diretiva():
    with pytest.raises(ContractError) as e:
        build_ir([pkt(fields=[("a", "uint8")], endian="middle", line=7)])
    assert (e.value.diagnostics[0].line, e.value.diagnostics[0].column) == (7, 10)


def test_little_endian_exige_campos_multiplos_de_8():
    msgs = errors(pkt(fields=[("a", "uint12"), ("b", "uint4")], endian="little"))
    assert len([m for m in msgs if "little-endian" in m]) == 2  # um erro por campo
    assert errors(pkt(fields=[("f", "bool"), ("g", "uint7")], endian="little"))


def test_little_endian_alinhado_e_valido():
    p = one(pkt(fields=[("a", "uint8"), ("b", "int16"), ("c", "uint64")], endian="little"))
    assert [f.offset for f in p.fields] == [0, 8, 24]


# ---------------------------------------------------------------- tamanho total

@pytest.mark.parametrize("campos", [[("a", "uint12")], [("a", "bool")], [("a", "uint8"), ("b", "uint3")]])
def test_tamanho_total_precisa_ser_multiplo_de_8(campos):
    assert any("múltiplo de 8" in m for m in errors(pkt(fields=campos)))


def test_tamanho_total_multiplo_de_8_com_campos_pequenos():
    assert one(pkt(fields=[(f"b{i}", "bool") for i in range(8)])).total_bytes == 1


def test_pacote_sem_campos():
    assert any("não tem campos" in m for m in errors(pkt(fields=[])))


# --------------------------------------------------------- coleta de erros

def test_coleta_todos_os_erros_de_uma_vez():
    msgs = errors(pkt("A", [("x", "float32"), ("x", "uint8"), ("clk", "uint99"), ("y", "uint3")], endian="middle"))
    joined = " | ".join(msgs)
    for trecho in ("endianness inválida", "tipo desconhecido", "já declarado", "reservada", "excede", "múltiplo de 8"):
        assert trecho in joined, trecho


def test_erro_em_um_pacote_nao_esconde_erros_de_outro():
    msgs = errors(pkt("A", [("x", "float32")]), pkt("B", [("y", "uint3")], line=5))
    assert any("tipo desconhecido" in m for m in msgs) and any("pacote 'B'" in m and "múltiplo" in m for m in msgs)


def test_diagnosticos_sempre_tem_posicao():
    with pytest.raises(ContractError) as e:
        build_ir([pkt("A", [("x", "float32"), ("x", "uint8"), ("y", "uint3")])])
    assert all(d.line > 0 and d.column > 0 for d in e.value.diagnostics)
    assert e.value.diagnostics[0].format("c.hidl").startswith("c.hidl:")
