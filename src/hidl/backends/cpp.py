"""Back-end C++: IR -> cabeçalho `.hpp` autocontido (header-only, C++11).

Para cada pacote gera uma `struct` com os campos já tipados, `kSizeBytes`,
`static bool decode(buf, len, out)` e `bool encode(buf, len) const`.
As regras de bits seguem docs/SPEC_MAPEAMENTO.md; este arquivo só as implementa.
"""

from __future__ import annotations

from ..ir import BOOL, INT, IRField, IRPacket

_RUNTIME = """\
namespace detail {

// Big-endian de rede: o bit 0 do pacote é o MSB do byte 0 (SPEC, seção 3).
inline std::uint64_t read_be(const std::uint8_t* b, std::size_t off, unsigned w) {
    std::uint64_t v = 0;
    for (unsigned i = 0; i < w; ++i) {
        const std::size_t bit = off + i;
        v = (v << 1) | ((b[bit >> 3] >> (7 - (bit & 7))) & 1u);
    }
    return v;
}

inline void write_be(std::uint8_t* b, std::size_t off, unsigned w, std::uint64_t v) {
    for (unsigned i = 0; i < w; ++i) {
        const std::size_t bit = off + w - 1 - i;
        const std::uint8_t mask = static_cast<std::uint8_t>(1u << (7 - (bit & 7)));
        if ((v >> i) & 1u) b[bit >> 3] = static_cast<std::uint8_t>(b[bit >> 3] | mask);
        else               b[bit >> 3] = static_cast<std::uint8_t>(b[bit >> 3] & ~mask);
    }
}

// Little-endian: só para campos alinhados em byte (off e w múltiplos de 8).
inline std::uint64_t read_le(const std::uint8_t* b, std::size_t off, unsigned w) {
    std::uint64_t v = 0;
    for (unsigned i = 0; i < w / 8; ++i)
        v |= static_cast<std::uint64_t>(b[off / 8 + i]) << (8 * i);
    return v;
}

inline void write_le(std::uint8_t* b, std::size_t off, unsigned w, std::uint64_t v) {
    for (unsigned i = 0; i < w / 8; ++i)
        b[off / 8 + i] = static_cast<std::uint8_t>((v >> (8 * i)) & 0xFFu);
}

inline std::int64_t sign_extend(std::uint64_t v, unsigned w) {
    if (w < 64 && ((v >> (w - 1)) & 1u)) v |= (~std::uint64_t{0}) << w;
    return static_cast<std::int64_t>(v);
}

}  // namespace detail
"""


def ctype(f: IRField) -> str:
    if f.kind == BOOL:
        return "bool"
    bits = 8 if f.width <= 8 else 16 if f.width <= 16 else 32 if f.width <= 32 else 64
    return f"std::{'int' if f.kind == INT else 'uint'}{bits}_t"


def _decode_expr(p: IRPacket, f: IRField) -> str:
    raw = f"detail::read_{'be' if p.endian == 'big' else 'le'}(buf, {f.offset}, {f.width})"
    if f.kind == BOOL:
        return f"{raw} != 0"
    if f.kind == INT:
        return f"static_cast<{ctype(f)}>(detail::sign_extend({raw}, {f.width}))"
    return f"static_cast<{ctype(f)}>({raw})"


def _encode_value(f: IRField) -> str:
    if f.kind == BOOL:
        return f"({f.name} ? 1u : 0u)"
    if f.kind == INT:
        return f"static_cast<std::uint64_t>(static_cast<std::int64_t>({f.name}))"
    return f"static_cast<std::uint64_t>({f.name})"


def _packet(p: IRPacket) -> list[str]:
    e = "be" if p.endian == "big" else "le"
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
        o.append(f"        detail::write_{e}(buf, {f.offset}, {f.width}, {_encode_value(f)});")
    o += ["        return true;", "    }", "};", ""]
    return o


def generate(packets: list[IRPacket], source_name: str = "contrato.hidl") -> str:
    out = [
        f"// Gerado por hidl a partir de {source_name}. NÃO EDITE À MÃO.",
        "#pragma once",
        "",
        "#include <cstddef>",
        "#include <cstdint>",
        "",
        "namespace hidl {",
        "",
        _RUNTIME,
    ]
    for p in packets:
        out += _packet(p)
    out.append("}  // namespace hidl")
    out.append("")
    return "\n".join(out)
