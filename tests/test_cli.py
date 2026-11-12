import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hidl.cli import main

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"


def test_check_aceita_exemplos_validos(capsys):
    for nome in ("telemetria", "calculadora", "little"):
        assert main(["compile", str(EX / f"{nome}.hidl"), "--check"]) == 0
    assert "ok (2 pacote(s))" in capsys.readouterr().out


def test_check_rejeita_invalido_com_todos_os_erros(capsys):
    assert main(["compile", str(EX / "invalido.hidl"), "--check"]) == 1
    err = capsys.readouterr().err
    assert "invalido.hidl:2:5: erro: 'clk' é palavra reservada" in err
    assert "tipo desconhecido 'float32'" in err and "múltiplo de 8" in err


def test_erro_de_sintaxe_sai_com_1(tmp_path, capsys):
    f = tmp_path / "x.hidl"
    f.write_text("packet P { a uint8; }")
    assert main(["compile", str(f)]) == 1
    assert f"{f}:1:14: erro: esperava ':'" in capsys.readouterr().err


def test_arquivo_inexistente(tmp_path, capsys):
    assert main(["compile", str(tmp_path / "nao_existe.hidl")]) == 1
    assert "não foi possível ler" in capsys.readouterr().err


def test_ir_texto_e_json(capsys):
    assert main(["compile", str(EX / "telemetria.hidl"), "--ir", "--json"]) == 0
    out = capsys.readouterr().out
    assert "velocidade" in out and "offset" in out
    dados = json.loads(out[out.index("["):])
    assert dados[0]["fields"][1] == {"name": "velocidade", "kind": "uint", "width": 32, "offset": 16}


def test_gera_cpp(tmp_path):
    saida = tmp_path / "t.hpp"
    assert main(["compile", str(EX / "telemetria.hidl"), "--cpp", str(saida)]) == 0
    assert "struct Telemetria" in saida.read_text()


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ não encontrado")
def test_demo_ponta_a_ponta():
    r = subprocess.run([str(ROOT / "demo" / "run_demo.sh"), "1000", "-250"], capture_output=True, text=True, check=True)
    assert "pacote Operandos  : 03 E8 FF 06" in r.stdout
    assert "soma = 750, diferenca = 1250" in r.stdout
    assert "pacote Resultado  : 00 00 02 EE 00 00 04 E2" in r.stdout
