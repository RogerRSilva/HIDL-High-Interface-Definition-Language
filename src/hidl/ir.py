"""Representação intermediária (IR): único ponto de verdade dos back-ends.

Cada campo tem tipo, largura em bits e offset em bits a partir do MSB do
primeiro byte do pacote (ver docs/SPEC_MAPEAMENTO.md, seção 3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

UINT, INT, BOOL = "uint", "int", "bool"


@dataclass(frozen=True)
class IRField:
    name: str
    kind: str  # "uint" | "int" | "bool"
    width: int  # bits
    offset: int  # bits desde o MSB do primeiro byte

    @property
    def signed(self) -> bool:
        return self.kind == INT

    @property
    def type_name(self) -> str:
        return "bool" if self.kind == BOOL else f"{self.kind}{self.width}"


@dataclass(frozen=True)
class IRPacket:
    name: str
    endian: str  # "big" | "little"
    fields: tuple[IRField, ...]

    @property
    def total_bits(self) -> int:
        return sum(f.width for f in self.fields)

    @property
    def total_bytes(self) -> int:
        return self.total_bits // 8


def to_text(packets: list[IRPacket]) -> str:
    """Dump legível da IR (marco da Fase 2)."""
    out: list[str] = []
    for p in packets:
        out.append(f"packet {p.name}  endian={p.endian}  {p.total_bits} bits ({p.total_bytes} bytes)")
        out.append(f"  {'offset':>6}  {'largura':>7}  {'tipo':<8} campo")
        for f in p.fields:
            out.append(f"  {f.offset:>6}  {f.width:>7}  {f.type_name:<8} {f.name}")
        out.append("")
    return "\n".join(out)


def to_json(packets: list[IRPacket]) -> str:
    return json.dumps(
        [
            {
                "name": p.name,
                "endian": p.endian,
                "total_bits": p.total_bits,
                "fields": [
                    {"name": f.name, "kind": f.kind, "width": f.width, "offset": f.offset}
                    for f in p.fields
                ],
            }
            for p in packets
        ],
        indent=2,
    )
