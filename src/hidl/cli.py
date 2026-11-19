"""Linha de comando:  hidl compile contrato.hidl [--check] [--ir] [--json] [--cpp SAIDA.hpp [--standalone]]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .backends.cpp import RUNTIME_INCLUDE, generate as generate_cpp, runtime_source
from .errors import ContractError
from .ir import to_json, to_text
from .parser import parse
from .semantic import build_ir


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="hidl", description="HIDL — compilador de contratos CPU–FPGA")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile", help="compila um contrato .hidl")
    c.add_argument("contrato", type=Path)
    c.add_argument("--check", action="store_true", help="só valida o contrato")
    c.add_argument("--ir", action="store_true", help="imprime a IR com offsets")
    c.add_argument("--json", action="store_true", help="imprime a IR em JSON")
    c.add_argument("--cpp", metavar="SAIDA.hpp", type=Path, help="gera o cabeçalho C++")
    c.add_argument("--standalone", action="store_true",
                   help="com --cpp: embute o runtime no .hpp em vez de gravar hidl/runtime.hpp ao lado dele")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    path: Path = args.contrato
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"{path}: erro: não foi possível ler o arquivo ({e.strerror})", file=sys.stderr)
        return 1

    try:
        packets = build_ir(parse(source))
    except ContractError as e:
        for d in e.diagnostics:
            print(d.format(str(path)), file=sys.stderr)
        return 1

    if args.check:
        print(f"ok ({len(packets)} pacote(s))")
    if args.ir:
        print(to_text(packets))
    if args.json:
        print(to_json(packets))
    if args.cpp:
        try:
            args.cpp.parent.mkdir(parents=True, exist_ok=True)
            args.cpp.write_text(generate_cpp(packets, path.name, standalone=args.standalone), encoding="utf-8")
            if not args.standalone:
                rt_path = args.cpp.parent / RUNTIME_INCLUDE
                rt_path.parent.mkdir(parents=True, exist_ok=True)
                rt_path.write_text(runtime_source(), encoding="utf-8")
        except OSError as e:
            print(f"{args.cpp}: erro: não foi possível escrever o arquivo ({e.strerror})", file=sys.stderr)
            return 1
        print(f"gerado: {args.cpp}")
        if not args.standalone:
            print(f"gerado: {rt_path}  (compile com -I{args.cpp.parent})")
    return 0
