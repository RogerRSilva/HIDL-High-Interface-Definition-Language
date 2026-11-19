#!/usr/bin/env bash
# Contrato -> cabeçalho C++ -> binário -> execução. Requer python3 e g++.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
PYTHONPATH=src python3 -m hidl compile examples/calculadora.hidl --ir --cpp build/calculadora.hpp
g++ -std=c++11 -Wall -Wextra -pedantic -Ibuild demo/main.cpp -o build/calc
./build/calc "${1:-1000}" "${2:--250}"
