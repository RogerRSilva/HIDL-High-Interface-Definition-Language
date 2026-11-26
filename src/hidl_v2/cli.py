"""CLI da V2: hidl-v2 compile contrato.hidl --verilog saida.v"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hidl.errors import ContractError
from hidl.parser import parse
from hidl.semantic import build_ir

from .verilog import generate


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hidl-v2",
        description="HIDL V2 — geração de layouts em Verilog-2001",
    )
    commands = parser.add_subparsers(dest="cmd", required=True)
    compile_parser = commands.add_parser("compile", help="compila um contrato .hidl")
    compile_parser.add_argument("contrato", type=Path)
    compile_parser.add_argument(
        "--verilog", metavar="SAIDA.v", type=Path, help="gera os módulos Verilog"
    )
    compile_parser.add_argument(
        "--check", action="store_true", help="só valida o contrato"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.check and not args.verilog:
        parser.error("informe --verilog SAIDA.v ou --check")

    path: Path = args.contrato
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        print(
            f"{path}: erro: não foi possível ler o arquivo ({error.strerror})",
            file=sys.stderr,
        )
        return 1

    try:
        packets = build_ir(parse(source))
    except ContractError as error:
        for diagnostic in error.diagnostics:
            print(diagnostic.format(str(path)), file=sys.stderr)
        return 1

    if args.check:
        print(f"ok ({len(packets)} pacote(s))")
    if args.verilog:
        try:
            args.verilog.parent.mkdir(parents=True, exist_ok=True)
            args.verilog.write_text(
                generate(packets, path.name),
                encoding="utf-8",
            )
        except OSError as error:
            print(
                f"{args.verilog}: erro: não foi possível escrever o arquivo "
                f"({error.strerror})",
                file=sys.stderr,
            )
            return 1
        print(f"gerado: {args.verilog}")
    return 0
