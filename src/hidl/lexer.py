"""Lexer: texto do contrato -> lista de tokens (com linha:coluna).

Tokens do MVP:  IDENT  {  }  :  ;  EOF
Palavras como `packet` e `endian` são IDENT comuns: quem decide o que são é o
parser. Assim, um campo chamado `packet` chega até a semântica, que o rejeita
como "palavra reservada" com a mensagem certa.

Comentários: `// até o fim da linha` e `# até o fim da linha`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ContractError, Diagnostic

IDENT, LBRACE, RBRACE, COLON, SEMI, EOF = "IDENT", "{", "}", ":", ";", "EOF"

_PUNCT = {"{": LBRACE, "}": RBRACE, ":": COLON, ";": SEMI}


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    line: int
    column: int


def _is_ident_start(c: str) -> bool:
    return c == "_" or ("a" <= c <= "z") or ("A" <= c <= "Z")


def _is_ident_part(c: str) -> bool:
    return _is_ident_start(c) or ("0" <= c <= "9")


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    diags: list[Diagnostic] = []
    i, line, col, n = 0, 1, 1, len(source)

    while i < n:
        c = source[i]
        if c == "\n":
            i, line, col = i + 1, line + 1, 1
        elif c in " \t\r":
            i, col = i + 1, col + 1
        elif c == "#" or source.startswith("//", i):
            while i < n and source[i] != "\n":
                i, col = i + 1, col + 1
        elif c in _PUNCT:
            tokens.append(Token(_PUNCT[c], c, line, col))
            i, col = i + 1, col + 1
        elif _is_ident_start(c):
            start, start_col = i, col
            while i < n and _is_ident_part(source[i]):
                i, col = i + 1, col + 1
            tokens.append(Token(IDENT, source[start:i], line, start_col))
        else:
            diags.append(Diagnostic(f"caractere inesperado {c!r}", line, col))
            i, col = i + 1, col + 1

    if diags:  # o léxico coleta todos os caracteres inválidos de uma vez
        raise ContractError(diags)
    tokens.append(Token(EOF, "", line, col))
    return tokens
