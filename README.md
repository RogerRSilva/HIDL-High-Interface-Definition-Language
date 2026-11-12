# HIDL — Hardware Interface Definition Language (MVP)

Um contrato de texto descreve o pacote que trafega entre CPU e FPGA. O compilador gera,
a partir dele, o código C++ que lê e escreve esse pacote.

```
contrato .hidl → lexer → parser → AST → semantic.build_ir → IR → backends/cpp → .hpp
```

```
src/hidl/lexer.py      texto → tokens (linha:coluna)
src/hidl/parser.py     tokens → AST (descendente recursivo; gramática no docstring)
src/hidl/ast.py        PacketDecl / FieldDecl
src/hidl/semantic.py   build_ir(decls): validações + offsets
src/hidl/ir.py         IRPacket / IRField (imutáveis), to_text / to_json
src/hidl/backends/cpp.py  IR → cabeçalho C++ autocontido
src/hidl/cli.py        hidl compile ...
docs/SPEC_MAPEAMENTO.md   regras de bits e mapeamento (referência dos back-ends)
examples/              contratos de exemplo (válidos e um inválido)
demo/                  soma e subtração com o C++ gerado
tests/                 91 testes (inclui compilar e executar o C++ gerado)
```

## Uso

```bash
pip install pytest          # só para os testes
pip install -e .            # opcional: instala o comando `hidl`

python -m hidl compile examples/telemetria.hidl --check
python -m hidl compile examples/telemetria.hidl --ir
python -m hidl compile examples/telemetria.hidl --json
python -m hidl compile examples/telemetria.hidl --cpp build/telemetria.hpp
python -m hidl compile examples/invalido.hidl --check     # erros com arquivo:linha:coluna
```
(com `PYTHONPATH=src` se não instalou o pacote.)

## Demo: soma e subtração

```bash
./demo/run_demo.sh 1000 -250     # requer python3 e g++
```
Gera `build/calculadora.hpp` a partir de `examples/calculadora.hidl`, compila `demo/main.cpp`
e roda. Saída esperada:

```
pacote Operandos  : 03 E8 FF 06
a = 1000, b = -250
soma = 750, diferenca = 1250
pacote Resultado  : 00 00 02 EE 00 00 04 E2
```

## Testes

```bash
pytest        # 91 passed (os testes que usam C++ são pulados se não houver g++)
```

Os testes do back-end geram o `.hpp`, compilam com `-Wall -Wextra -pedantic -Werror`, e
comparam `encode`/`decode` com uma referência em Python (valores mínimos, máximos e aleatórios,
em big e little-endian, até 64 bits).

## Limites do MVP

Só C++ (sem Verilog ainda); sem structs aninhados, arrays ou campos condicionais; `little`
exige campos alinhados em byte; sem padding automático. Veja `docs/SPEC_MAPEAMENTO.md`.
