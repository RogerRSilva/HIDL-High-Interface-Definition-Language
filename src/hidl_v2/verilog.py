"""Back-end Verilog-2001: IR -> módulos combinacionais de empacotamento."""

from __future__ import annotations

from hidl.ir import INT, IRField, IRPacket


def _width_range(width: int) -> str:
    return "" if width == 1 else f"[{width - 1}:0] "


def _field_type(f: IRField) -> str:
    signed = "signed " if f.kind == INT else ""
    return f"{signed}{_width_range(f.width)}"


def _packet_module(packet: IRPacket) -> list[str]:
    module_name = f"hidl_codec_{packet.name}"
    ports = [
        f"    input [{packet.total_bits - 1}:0] packed_in",
        *[
            f"    output {_field_type(field)}out_{field.name}"
            for field in packet.fields
        ],
        *[
            f"    input {_field_type(field)}in_{field.name}"
            for field in packet.fields
        ],
        f"    output [{packet.total_bits - 1}:0] packed_out",
    ]

    out = [
        f"// {packet.name}: {packet.total_bits} bits, {packet.endian}-endian",
        f"module {module_name}(",
        ",\n".join(ports),
        ");",
        "",
    ]

    for field in packet.fields:
        if packet.endian == "big":
            high = packet.total_bits - field.offset - 1
            low = high - field.width + 1
            packed_slice = f"[{high}:{low}]"
            out.append(f"assign out_{field.name} = packed_in{packed_slice};")
            out.append(f"assign packed_out{packed_slice} = in_{field.name};")
        else:
            for byte_index in range(field.width // 8):
                offset = field.offset + byte_index * 8
                high = packet.total_bits - offset - 1
                low = high - 7
                value_high = byte_index * 8 + 7
                value_low = byte_index * 8
                packed_slice = f"[{high}:{low}]"
                value_slice = f"[{value_high}:{value_low}]"
                out.append(
                    f"assign out_{field.name}{value_slice} = packed_in{packed_slice};"
                )
                out.append(
                    f"assign packed_out{packed_slice} = in_{field.name}{value_slice};"
                )

    out += ["", "endmodule", ""]
    return out


def generate(packets: list[IRPacket], source_name: str = "contrato.hidl") -> str:
    out = [
        f"// Gerado por HIDL V2 a partir de {source_name}. NÃO EDITE À MÃO.",
        "// Verilog-2001; cada módulo converte entre campos e o vetor do pacote.",
        "",
    ]
    for packet in packets:
        out.extend(_packet_module(packet))
    return "\n".join(out)
