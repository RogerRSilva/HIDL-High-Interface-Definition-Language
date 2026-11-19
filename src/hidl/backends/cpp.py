"""Back-end C++: IR -> cabeçalho `.hpp` (header-only, C++11).

Para cada pacote gera uma `struct` com os campos já tipados, `kSizeBytes`,
`static bool decode(buf, len, out)` e `bool encode(buf, len) const`.

A lógica de bits (ler/escrever N bits em um offset, endianness, extensão de sinal) não é
emitida aqui: mora no runtime fixo `hidl/runtime.hpp` (src/hidl/runtime/), que implementa
docs/SPEC_MAPEAMENTO.md e é testado uma vez só. O código gerado só traz o que varia com o
contrato. Com `standalone=True` o runtime é embutido no próprio arquivo gerado.
"""

from __future__ import annotations

from pathlib import Path

from ..ir import BOOL, INT, IRField, IRPacket

# Deve coincidir com HIDL_RUNTIME_ABI em runtime/hidl/runtime.hpp (há teste para isso).
RUNTIME_ABI = 1
RUNTIME_INCLUDE = "hidl/runtime.hpp"


def runtime_dir() -> Path:
    """Diretório a passar em `-I` para encontrar `hidl/runtime.hpp`."""
    return Path(__file__).resolve().parent.parent / "runtime"


def runtime_source() -> str:
    return (runtime_dir() / RUNTIME_INCLUDE).read_text(encoding="utf-8")


def ctype(f: IRField) -> str:
    if f.kind == BOOL:
        return "bool"
    bits = 8 if f.width <= 8 else 16 if f.width <= 16 else 32 if f.width <= 32 else 64
    return f"std::{'int' if f.kind == INT else 'uint'}{bits}_t"


def _decode_expr(p: IRPacket, f: IRField) -> str:
    return f"rt::read_{'be' if p.endian == 'big' else 'le'}<{ctype(f)}, {f.offset}, {f.width}>(buf)"


def _encode_stmt(p: IRPacket, f: IRField) -> str:
    return f"rt::write_{'be' if p.endian == 'big' else 'le'}<{ctype(f)}, {f.offset}, {f.width}>(buf, {f.name});"


def _packet(p: IRPacket) -> list[str]:
    o = [f"// {p.name}: {p.total_bits} bits ({p.total_bytes} bytes), {p.endian}-endian"]
    o.append(f"struct {p.name} {{")
    for f in p.fields:
        o.append(f"    {ctype(f)} {f.name}{{}};  // {f.type_name}, bits [{f.offset}..{f.offset + f.width - 1}]")
    o += ["", f"    static constexpr std::size_t kSizeBytes = {p.total_bytes};", ""]

    o.append(f"    static bool decode(const std::uint8_t* buf, std::size_t len, {p.name}& out) {{")
    o.append("        if (len < kSizeBytes) return false;")
    for f in p.fields:
        o.append(f"        out.{f.name} = {_decode_expr(p, f)};")
    o += ["        return true;", "    }", ""]

    o.append("    bool encode(std::uint8_t* buf, std::size_t len) const {")
    o.append("        if (len < kSizeBytes) return false;")
    o.append("        for (std::size_t i = 0; i < kSizeBytes; ++i) buf[i] = 0;")
    for f in p.fields:
        o.append(f"        {_encode_stmt(p, f)}")
    o += ["        return true;", "    }", "};", ""]
    return o


def _runtime_block(standalone: bool) -> list[str]:
    if standalone:
        # O runtime tem include guard próprio: seguro misturar com outros headers gerados.
        return ["// ---- hidl/runtime.hpp (embutido: --standalone) ----", runtime_source().rstrip("\n"),
                "// ---- fim de hidl/runtime.hpp ----"]
    return [f'#include "{RUNTIME_INCLUDE}"']


def generate(packets: list[IRPacket], source_name: str = "contrato.hidl", standalone: bool = False) -> str:
    out = [
        f"// Gerado por hidl a partir de {source_name}. NÃO EDITE À MÃO.",
        "#pragma once",
        "",
        "#include <cstddef>",
        "#include <cstdint>",
        "",
        *_runtime_block(standalone),
        "",
        f"static_assert(HIDL_RUNTIME_ABI == {RUNTIME_ABI},",
        f'              "{source_name} foi gerado para outra versão do runtime HIDL: regenere com o compilador hidl");',
        "",
        "namespace hidl {",
        "",
    ]
    for p in packets:
        out += _packet(p)
    out.append("}  // namespace hidl")
    out.append("")
    return "\n".join(out)
