from pathlib import Path

from hidl_v2.cli import main


ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def test_cli_generates_verilog(tmp_path, capsys):
    output = tmp_path / "nested" / "telemetria.v"

    assert main(
        ["compile", str(EXAMPLES / "telemetria.hidl"), "--verilog", str(output)]
    ) == 0

    assert "gerado:" in capsys.readouterr().out
    assert "module hidl_codec_Telemetria(" in output.read_text(encoding="utf-8")
    assert "module hidl_codec_Status(" in output.read_text(encoding="utf-8")


def test_cli_check_validates_without_output_file(capsys):
    assert main(["compile", str(EXAMPLES / "calculadora.hidl"), "--check"]) == 0
    assert "ok (2 pacote(s))" in capsys.readouterr().out


def test_cli_rejects_invalid_contract(capsys):
    assert main(["compile", str(EXAMPLES / "invalido.hidl"), "--check"]) == 1
    assert "invalido.hidl" in capsys.readouterr().err
