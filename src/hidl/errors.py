"""Diagnósticos do compilador (erros de sintaxe e semântica com posição)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnostic:
    message: str
    line: int = 0
    column: int = 0

    def format(self, filename: str) -> str:
        pos = f"{filename}:{self.line}:{self.column}" if self.line else filename
        return f"{pos}: erro: {self.message}"


class ContractError(Exception):
    """Contrato inválido. Carrega um ou mais diagnósticos."""

    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics
        super().__init__("; ".join(d.message for d in diagnostics))
