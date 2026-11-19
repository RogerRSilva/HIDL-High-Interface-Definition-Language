"""Testes do runtime C++ (hidl/runtime.hpp) isolado, sem passar pelo gerador."""

import shutil
import subprocess
from pathlib import Path

import pytest

from hidl.backends.cpp import runtime_dir

needs_gpp = pytest.mark.skipif(shutil.which("g++") is None, reason="g++ não encontrado")
GCC = ["g++", "-std=c++11", "-Wall", "-Wextra", "-pedantic", "-Werror", "-I", str(runtime_dir())]
CPP = Path(__file__).parent / "cpp" / "test_runtime.cpp"


@needs_gpp
def test_runtime_contra_logica_bit_a_bit(tmp_path):
    exe = tmp_path / "t"
    subprocess.run(GCC + [str(CPP), "-o", str(exe)], check=True)
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    assert " 0 falhas" in r.stdout


@needs_gpp
def test_runtime_tambem_compila_em_cxx17_e_com_otimizacao(tmp_path):
    exe = tmp_path / "t"
    subprocess.run(GCC[:1] + ["-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic", "-Werror", "-I", str(runtime_dir()),
                              str(CPP), "-o", str(exe)], check=True)
    assert subprocess.run([str(exe)], capture_output=True).returncode == 0


def _compila(tmp_path, corpo):
    f = tmp_path / "m.cpp"
    f.write_text(f'#include "hidl/runtime.hpp"\nint main() {{ unsigned char b[16] = {{0}}; {corpo} return 0; }}\n')
    return subprocess.run(GCC + [str(f), "-o", str(tmp_path / "m")], capture_output=True, text=True)


@needs_gpp
@pytest.mark.parametrize("corpo, mensagem", [
    ("(void)hidl::rt::read_le<unsigned, 3, 16>(b);", "little-endian exige campo alinhado em byte"),
    ("(void)hidl::rt::read_le<unsigned, 0, 12>(b);", "little-endian exige campo alinhado em byte"),
    ("(void)hidl::rt::read_be<unsigned char, 0, 9>(b);", "tipo C++ menor que a largura do campo"),
    ("(void)hidl::rt::read_be<unsigned long long, 0, 65>(b);", "largura deve estar em [1, 64]"),
    ("(void)hidl::rt::read_be<float, 0, 16>(b);", "tipo de campo deve ser inteiro"),
])
def test_usos_invalidos_viram_erro_de_compilacao(tmp_path, corpo, mensagem):
    r = _compila(tmp_path, corpo)
    assert r.returncode != 0 and mensagem in r.stderr


@needs_gpp
def test_uso_valido_compila(tmp_path):
    assert _compila(tmp_path, "(void)hidl::rt::read_le<unsigned, 8, 16>(b); (void)hidl::rt::read_be<bool, 3, 1>(b);").returncode == 0
