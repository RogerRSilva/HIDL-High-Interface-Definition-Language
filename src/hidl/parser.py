"""Parser descendente recursivo: tokens -> AST (list[PacketDecl]).

Gramática (EBNF) do MVP:

    contrato := pacote*
    pacote   := "packet" IDENT [ "endian" IDENT ] "{" campo* "}"
    campo    := IDENT ":" IDENT ";"

O valor depois de `endian` é lido como IDENT qualquer; se não for `big` ou
`little`, quem reclama é a semântica (com a posição guardada em `endian_pos`).
O parser só cuida de sintaxe: não conhece tipos nem limites.
"""

from __future__ import annotations

from .ast import FieldDecl, PacketDecl
from .errors import ContractError, Diagnostic
from .lexer import COLON, EOF, IDENT, LBRACE, RBRACE, SEMI, Token, tokenize


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.toks = tokens
        self.pos = 0

    # ---- utilidades -------------------------------------------------
    @property
    def cur(self) -> Token:
        return self.toks[self.pos]

    def _describe(self, t: Token) -> str:
        return "fim do arquivo" if t.kind == EOF else f"'{t.text}'"

    def _fail(self, expected: str) -> ContractError:
        t = self.cur
        return ContractError([Diagnostic(
            f"esperava {expected}, encontrei {self._describe(t)}", t.line, t.column)])

    def _expect(self, kind: str, expected: str) -> Token:
        if self.cur.kind != kind:
            raise self._fail(expected)
        t = self.cur
        self.pos += 1
        return t

    def _is_word(self, word: str) -> bool:
        return self.cur.kind == IDENT and self.cur.text == word

    # ---- regras -----------------------------------------------------
    def contract(self) -> list[PacketDecl]:
        packets = []
        while self.cur.kind != EOF:
            packets.append(self.packet())
        return packets

    def packet(self) -> PacketDecl:
        if not self._is_word("packet"):
            raise self._fail("'packet'")
        self.pos += 1
        name = self._expect(IDENT, "o nome do pacote")

        endian: str | None = None
        endian_pos = (0, 0)
        if self._is_word("endian"):
            self.pos += 1
            val = self._expect(IDENT, "'big' ou 'little' depois de 'endian'")
            endian, endian_pos = val.text, (val.line, val.column)

        self._expect(LBRACE, "'{'")
        fields: list[FieldDecl] = []
        while self.cur.kind != RBRACE:
            if self.cur.kind == EOF:
                raise self._fail("'}'")
            fields.append(self.field())
        self._expect(RBRACE, "'}'")
        return PacketDecl(name.text, endian, endian_pos, fields, name.line, name.column)

    def field(self) -> FieldDecl:
        name = self._expect(IDENT, "o nome do campo")
        self._expect(COLON, "':' depois do nome do campo")
        typ = self._expect(IDENT, "o tipo do campo (ex.: uint16)")
        self._expect(SEMI, "';' no fim do campo")
        return FieldDecl(name.text, typ.text, name.line, name.column)


def parse(source: str) -> list[PacketDecl]:
    return _Parser(tokenize(source)).contract()
