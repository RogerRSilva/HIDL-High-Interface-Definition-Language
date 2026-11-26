# HIDL — Hardware Interface Definition Language (MVP)

Um contrato de texto descreve o pacote que trafega entre CPU e FPGA. A V1 gera um cabeçalho
C++ para ler e escrever o pacote; a V2 gera layouts em Verilog-2001.

```
contrato .hidl → lexer → parser → AST → semantic.build_ir → IR → backends/cpp → .hpp
                                                             └→ hidl_v2/verilog.py → .v
```

```
src/hidl/lexer.py      texto → tokens (linha:coluna)
src/hidl/parser.py     tokens → AST (descendente recursivo; gramática no docstring)
src/hidl/ast.py        PacketDecl / FieldDecl
src/hidl/semantic.py   build_ir(decls): validações + offsets
src/hidl/ir.py         IRPacket / IRField (imutáveis), to_text / to_json
src/hidl/backends/cpp.py  IR → cabeçalho C++ autocontido
src/hidl/cli.py        hidl compile ...
src/hidl_v2/           CLI e back-end Verilog-2001
docs/SPEC_MAPEAMENTO.md   regras de bits e mapeamento (referência dos back-ends)
examples/              contratos de exemplo (válidos e um inválido)
demo/                  soma e subtração com o C++ gerado
tests/                 testes do front-end e dos back-ends C++ e Verilog
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

## V2: geração de layouts em Verilog

A V2 mantém a CLI e o back-end C++ existentes e acrescenta um comando separado para gerar
Verilog-2001 a partir dos mesmos contratos. Cada pacote gera um módulo combinacional que
converte entre um vetor de bits (`packed_in`/`packed_out`) e os campos do pacote (`out_*`/`in_*`).
Isso representa o layout e a conversão do pacote; não gera lógica de aplicação, como a soma
e a subtração da demonstração.

```bash
python -m hidl_v2 compile examples/calculadora.hidl --verilog build/calculadora.v
python -m hidl_v2 compile examples/telemetria.hidl --check
```

O comando instalado é `hidl-v2`. Como na CLI atual, use `PYTHONPATH=src` se o pacote não estiver
instalado.

Veja [docs/TUTORIAL_FERRAMENTAS.md](./docs/TUTORIAL_FERRAMENTAS.md) para instalação das ferramentas
e comandos de geração, compilação e validação no Windows.

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
python -m pytest
```

Os testes do back-end C++ geram o `.hpp`, compilam com `-Wall -Wextra -pedantic -Werror`, e
comparam `encode`/`decode` com uma referência em Python (valores mínimos, máximos e aleatórios,
em big e little-endian, até 64 bits). Os testes da V2 verificam os layouts Verilog gerados.
Os testes que dependem de compiladores externos são ignorados quando eles não estão disponíveis
no `PATH` do processo que executa pytest.

## Limites do MVP

A V2 gera layouts e conversores de pacotes em Verilog, mas ainda não gera lógica de aplicação
(por exemplo, soma e subtração). Não há structs aninhados, arrays ou campos condicionais;
`little` exige campos alinhados em byte; não há padding automático. Veja
`docs/SPEC_MAPEAMENTO.md`.
