# Tutorial de ferramentas e execução (Windows)

Este tutorial usa os comandos executados para gerar e validar o projeto. A V1 produz um
cabeçalho C++; a V2 produz módulos de layout em Verilog-2001. O Verilog atual não implementa
a soma e a subtração da demonstração C++.

## Ferramentas

- **Python 3.10+**: executar o compilador HIDL.
- **MSYS2 UCRT64 e g++**: compilar e executar a demonstração C++.
- **Icarus Verilog**: compilar o arquivo `.v` gerado.
- **pytest** (opcional): executar os testes Python.

## Instalar as ferramentas

Execute no PowerShell:

```powershell
winget install --id Python.Python.3.12 -e
winget install --id MSYS2.MSYS2 -e
winget install --id Icarus.Verilog -e
```

Para o g++, abra **MSYS2 UCRT64** pelo menu Iniciar e instale o compilador:

```bash
pacman -Syu
```

Se o terminal pedir para fechar, abra novamente **MSYS2 UCRT64** e execute:

```bash
pacman -S --needed mingw-w64-ucrt-x86_64-gcc
g++ --version
```

Na validação, `g++` compilou a demonstração e o MSYS2 foi confirmado em `C:\msys64`.
Se `pacman` não for reconhecido, abra **MSYS2 UCRT64** pelo menu Iniciar: o texto `UCRT64`
no prompt, sozinho, não garante que o shell seja o terminal MSYS2.

O Icarus foi instalado com o comando acima. Nesta instalação, seus executáveis ficam em
`C:\iverilog\bin`. Para disponibilizá-los na janela atual do PowerShell:

```powershell
$env:Path += ";C:\iverilog\bin"
iverilog -V
```

Essa alteração do `PATH` vale apenas para a janela atual.

## Gerar os arquivos

Abra o PowerShell na pasta raiz do projeto e configure o Python instalado:

```powershell
$Python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$env:PYTHONPATH = "$PWD\src"
```

Gere o cabeçalho C++ da V1:

```powershell
& $Python -m hidl compile examples\calculadora.hidl --cpp build\calculadora.hpp
```

Gere o Verilog da V2:

```powershell
& $Python -m hidl_v2 compile examples\calculadora.hidl --verilog build\calculadora.v
```

Os arquivos ficam na pasta `build`. O comando da V2 gera módulos de empacotamento e
desempacotamento para os pacotes HIDL; ele ainda não gera lógica de aplicação.

## Compilar e executar a demonstração C++

No terminal **MSYS2 UCRT64**, navegue até a raiz do clone e execute:

```bash
g++ -std=c++11 -Wall -Wextra -pedantic -Ibuild demo/main.cpp -o build/calc.exe
./build/calc.exe 1000 -250
```

A saída esperada inclui:

```text
soma = 750, diferenca = 1250
```

## Validar o Verilog gerado

No PowerShell, a partir da raiz do projeto, compile o módulo com Icarus:

```powershell
iverilog -g2001 -s hidl_codec_Operandos -o build\check.vvp build\calculadora.v
```

Esse comando foi executado sem erros. `calculadora.v` é o código Verilog; `check.vvp` é a
saída compilada para o simulador. Para simular valores e observar resultados, ainda é
necessário um testbench, que não faz parte da geração atual.

## Testes Python (opcional)

Instale e execute pytest usando o interpretador Python instalado:

```powershell
& $Python -m pip install pytest
& $Python -m pytest tests\test_verilog_backend.py tests\test_v2_cli.py
```

Os testes focados da V2 passaram durante a validação. Os testes C++ da suíte completa são
ignorados quando `g++` não está disponível no `PATH` do processo que executa pytest.
