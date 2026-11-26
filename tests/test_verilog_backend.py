from hidl.parser import parse
from hidl.semantic import build_ir
from hidl_v2.verilog import generate


def _generate(source: str) -> str:
    return generate(build_ir(parse(source)))


def test_big_endian_generates_packed_and_field_slices():
    verilog = _generate(
        """
        packet Operandos {
            a: int16;
            b: int16;
        }
        """
    )

    assert "module hidl_codec_Operandos(" in verilog
    assert "input [31:0] packed_in" in verilog
    assert "output signed [15:0] out_a" in verilog
    assert "assign out_a = packed_in[31:16];" in verilog
    assert "assign packed_out[15:0] = in_b;" in verilog


def test_little_endian_reverses_bytes_within_each_field():
    verilog = _generate(
        """
        packet P endian little {
            a: uint16;
            b: uint16;
        }
        """
    )

    assert "assign out_a[7:0] = packed_in[31:24];" in verilog
    assert "assign out_a[15:8] = packed_in[23:16];" in verilog
    assert "assign packed_out[31:24] = in_a[7:0];" in verilog
    assert "assign packed_out[23:16] = in_a[15:8];" in verilog
    assert "assign out_b[7:0] = packed_in[15:8];" in verilog


def test_single_bit_field_has_no_invalid_zero_width_range():
    verilog = _generate(
        """
        packet Status {
            ativo: bool;
            modo: uint3;
            nivel: uint4;
        }
        """
    )

    assert "output out_ativo" in verilog
    assert "input in_ativo" in verilog
    assert "assign out_ativo = packed_in[7:7];" in verilog
    assert "assign packed_out[7:7] = in_ativo;" in verilog
