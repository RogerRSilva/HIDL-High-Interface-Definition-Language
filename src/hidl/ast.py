"""AST produzida pelo front-end (sintaxe apenas, sem validação semântica)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldDecl:
    name: str
    type_name: str
    line: int
    column: int


@dataclass(frozen=True)
class PacketDecl:
    name: str
    endian: str | None  # None => padrão (big)
    endian_pos: tuple[int, int]
    fields: list[FieldDecl] = field(default_factory=list)
    line: int = 0
    column: int = 0
