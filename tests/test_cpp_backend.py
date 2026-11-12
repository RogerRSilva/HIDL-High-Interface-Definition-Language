"""Gera o .hpp, compila com g++ e confere encode/decode contra uma referência em Python.

A referência (bits via inteiros Python) é independente do gerador: se C++ e
spec divergirem, estes testes falham. Pulados se não houver g++.
"""

import random
import shutil
import subprocess

import pytest

from hidl.backends.cpp import ctype, generate
from hidl.ir import BOOL, INT
from hidl.parser import parse
from hidl.semantic import build_ir

CONTRATO = """
packet Telemetria { id: uint16; velocidade: uint32; }
packet Bits { ativo: bool; modo: uint3; nivel: int4; sinal: int12; extra: uint4; }
packet Grande { a: uint64; b: int64; c: uint1; d: uint7; }
packet Pequeno endian little { canal: uint8; leitura: int16; carimbo: uint32; assinado: int64; }
"""
PACOTES = {p.name: p for p in build_ir(parse(CONTRATO))}

needs_gpp = pytest.mark.skipif(shutil.which("g++") is None, reason="g++ não encontrado")


# ------------------------------------------------------------ estático

def test_tipos_c_por_largura():
    p = {f.name: f for f in PACOTES["Bits"].fields}
    assert [ctype(p[n]) for n in ("ativo", "modo", "nivel", "sinal", "extra")] == [
        "bool", "std::uint8_t", "std::int8_t", "std::int16_t", "std::uint8_t"]


def test_cabecalho_tem_estrutura_esperada():
    h = generate(list(PACOTES.values()), "x.hidl")
    assert "#pragma once" in h and "struct Telemetria {" in h
    assert "kSizeBytes = 6;" in h and "kSizeBytes = 15;" in h
    assert "read_le(buf, 8, 16)" in h  # little-endian usa read_le


# ------------------------------------------------------------ referência

def ref_encode(pkt, values):
    if pkt.endian == "big":
        bits = "".join(format(v & ((1 << f.width) - 1), f"0{f.width}b") for f, v in zip(pkt.fields, values))
        return int(bits, 2).to_bytes(len(bits) // 8, "big").hex().upper()
    out = b""
    for f, v in zip(pkt.fields, values):
        out += (v & ((1 << f.width) - 1)).to_bytes(f.width // 8, "little")
    return out.hex().upper()


def sample_values(pkt, rng):
    def ranges(f):
        if f.kind == BOOL:
            return 0, 1
        if f.kind == INT:
            return -(1 << (f.width - 1)), (1 << (f.width - 1)) - 1
        return 0, (1 << f.width) - 1
    sets = [[ranges(f)[0] for f in pkt.fields], [ranges(f)[1] for f in pkt.fields]]
    sets += [[rng.randint(*ranges(f)) for f in pkt.fields] for _ in range(40)]
    return sets


def harness(pkt):
    lines = ['#include <cstdio>', '#include <cstdlib>', '#include <cstring>', '#include "t.hpp"',
             "int main(int, char** argv) {", f"  using P = hidl::{pkt.name};", "  P p;"]
    lines.append('  if (std::strcmp(argv[1], "enc") == 0) {')
    for i, f in enumerate(pkt.fields):
        conv = "strtoll" if f.kind == INT else "strtoull"
        lines.append(f"    p.{f.name} = static_cast<decltype(p.{f.name})>(std::{conv}(argv[{i + 2}], nullptr, 10));")
    lines += ["    unsigned char b[P::kSizeBytes]; p.encode(b, sizeof b);",
              '    for (unsigned char c : b) { std::printf("%02X", c); }',
              '    std::printf("\\n"); return 0; }',
              "  unsigned char b[P::kSizeBytes];",
              "  for (std::size_t i = 0; i < P::kSizeBytes; ++i) {",
              "    char h[3] = {argv[2][2*i], argv[2][2*i+1], 0}; b[i] = (unsigned char)std::strtoul(h, nullptr, 16); }",
              "  if (!P::decode(b, sizeof b, p)) return 2;"]
    for f in pkt.fields:
        fmt, cast = ("%lld", "long long") if f.kind == INT else ("%llu", "unsigned long long")
        lines.append(f'  std::printf("{fmt} ", ({cast})p.{f.name});')
    lines += ['  std::printf("\\n"); return 0; }']
    return "\n".join(lines)


@pytest.fixture(scope="module")
def binarios(tmp_path_factory):
    d = tmp_path_factory.mktemp("cpp")
    (d / "t.hpp").write_text(generate(list(PACOTES.values()), "teste.hidl"))
    exes = {}
    for name, pkt in PACOTES.items():
        (d / f"{name}.cpp").write_text(harness(pkt))
        subprocess.run(["g++", "-std=c++11", "-Wall", "-Wextra", "-pedantic", "-Werror", "-I", str(d),
                        str(d / f"{name}.cpp"), "-o", str(d / name)], check=True)
        exes[name] = str(d / name)
    return exes


@needs_gpp
@pytest.mark.parametrize("nome", list(PACOTES))
def test_encode_decode_contra_referencia(binarios, nome):
    pkt, rng = PACOTES[nome], random.Random(1234)
    for vals in sample_values(pkt, rng):
        esperado = ref_encode(pkt, vals)
        enc = subprocess.run([binarios[nome], "enc", *map(str, vals)], capture_output=True, text=True, check=True)
        assert enc.stdout.strip() == esperado, (nome, vals)
        dec = subprocess.run([binarios[nome], "dec", esperado], capture_output=True, text=True, check=True)
        assert list(map(int, dec.stdout.split())) == vals, (nome, vals)


@needs_gpp
def test_buffer_curto_e_rejeitado(tmp_path):
    (tmp_path / "t.hpp").write_text(generate([PACOTES["Telemetria"]]))
    (tmp_path / "m.cpp").write_text(
        '#include "t.hpp"\nint main(){ unsigned char b[5]={0}; hidl::Telemetria t;'
        ' return (!hidl::Telemetria::decode(b,5,t) && !t.encode(b,5)) ? 0 : 1; }')
    subprocess.run(["g++", "-std=c++11", "-I", str(tmp_path), str(tmp_path / "m.cpp"), "-o", str(tmp_path / "m")], check=True)
    assert subprocess.run([str(tmp_path / "m")]).returncode == 0
