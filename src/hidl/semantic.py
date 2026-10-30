"""Validação semântica: AST → IR (com offsets calculados)."""

from __future__ import annotations

import re

from .ast import PacketDecl
from .errors import ContractError, Diagnostic
from .ir import BOOL, INT, UINT, IRField, IRPacket

MAX_WIDTH = 64
_TYPE_RE = re.compile(r"^(uint|int)([1-9][0-9]*)$")

# Nomes que colidem com portas geradas no Verilog.
_VERILOG_PORTS = {"clk", "rst_n", "in_valid", "in_sof", "in_data", "out_valid"}
_VERILOG_KW = {
    "module", "endmodule", "input", "output", "inout", "wire", "reg", "integer", "assign",
    "always", "initial", "begin", "end", "if", "else", "case", "endcase", "for", "while",
    "posedge", "negedge", "parameter", "localparam", "function", "task", "signed", "default",
}
_CPP_KW = {
    "alignas", "auto", "break", "case", "char", "class", "const", "continue", "default", "do",
    "double", "else", "enum", "explicit", "extern", "false", "float", "for", "friend", "goto",
    "if", "inline", "long", "namespace", "new", "operator", "private", "protected", "public",
    "register", "return", "short", "signed", "sizeof", "static", "struct", "switch",
    "template", "this", "throw", "true", "try", "typedef", "union", "unsigned", "using",
    "virtual", "void", "volatile", "while", "decode", "encode",
}
# Palavras-chave do próprio contrato também são reservadas.
_HIDL_KW = {"packet", "endian"}
RESERVED = _HIDL_KW | _VERILOG_PORTS | _VERILOG_KW | _CPP_KW


def build_ir(decls: list[PacketDecl]) -> list[IRPacket]:
    diags: list[Diagnostic] = []
    packets: list[IRPacket] = []
    seen_packets: dict[str, int] = {}

    for d in decls:
        if d.name in seen_packets:
            diags.append(Diagnostic(
                f"pacote '{d.name}' já declarado na linha {seen_packets[d.name]}", d.line, d.column))
        seen_packets[d.name] = seen_packets.get(d.name, d.line)
        if d.name in RESERVED:
            diags.append(Diagnostic(f"'{d.name}' é palavra reservada", d.line, d.column))

        if not d.fields:
            diags.append(Diagnostic(f"pacote '{d.name}' não tem campos", d.line, d.column))

        endian = d.endian or "big"
        if endian not in ("big", "little"):
            diags.append(Diagnostic(
                f"endianness inválida '{endian}' (use 'big' ou 'little')", *d.endian_pos))
            endian = "big"

        offset = 0
        fields: list[IRField] = []
        names: dict[str, int] = {}
        for f in d.fields:
            if f.name in names:
                diags.append(Diagnostic(
                    f"campo '{f.name}' já declarado na linha {names[f.name]} do pacote '{d.name}'",
                    f.line, f.column))
            names[f.name] = names.get(f.name, f.line)
            if f.name in RESERVED:
                diags.append(Diagnostic(f"'{f.name}' é palavra reservada", f.line, f.column))

            parsed = _parse_type(f.type_name)
            if parsed is None:
                diags.append(Diagnostic(
                    f"tipo desconhecido '{f.type_name}' (use bool, uintN ou intN, 1 ≤ N ≤ {MAX_WIDTH})",
                    f.line, f.column))
                continue
            kind, width = parsed
            if width > MAX_WIDTH:
                diags.append(Diagnostic(
                    f"largura {width} excede o máximo de {MAX_WIDTH} bits no MVP", f.line, f.column))
                continue
            if kind == INT and width < 2:
                diags.append(Diagnostic("int1 não é suportado (use bool ou uint1)", f.line, f.column))
                continue
            if endian == "little" and width % 8 != 0:
                diags.append(Diagnostic(
                    f"campo '{f.name}' ({f.type_name}): em pacotes little-endian, "
                    "todos os campos devem ter largura múltipla de 8 bits", f.line, f.column))
                continue
            fields.append(IRField(f.name, kind, width, offset))
            offset += width

        if offset % 8 != 0:
            diags.append(Diagnostic(
                f"pacote '{d.name}' tem {offset} bits; o tamanho total deve ser múltiplo de 8 "
                "(adicione bits de preenchimento)", d.line, d.column))
        packets.append(IRPacket(d.name, endian, tuple(fields)))

    if diags:
        raise ContractError(diags)
    return packets


def _parse_type(name: str) -> tuple[str, int] | None:
    if name == "bool":
        return BOOL, 1
    m = _TYPE_RE.match(name)
    if not m:
        return None
    return (UINT if m.group(1) == "uint" else INT), int(m.group(2))
