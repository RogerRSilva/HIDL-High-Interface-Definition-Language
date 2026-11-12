// Demo: o contrato gerou calculadora.hpp; aqui a CPU só usa variáveis já organizadas.
// Uso: ./calc [a] [b]      (padrão: 1000 -250)
#include <cstdio>
#include <cstdlib>

#include "calculadora.hpp"

int main(int argc, char** argv) {
    const int a = argc > 1 ? std::atoi(argv[1]) : 1000;
    const int b = argc > 2 ? std::atoi(argv[2]) : -250;

    // Simula o que o FPGA entregaria: bytes brutos do pacote Operandos.
    hidl::Operandos entrada;
    entrada.a = static_cast<std::int16_t>(a);
    entrada.b = static_cast<std::int16_t>(b);
    std::uint8_t fio[hidl::Operandos::kSizeBytes];
    entrada.encode(fio, sizeof fio);

    std::printf("pacote Operandos  :");
    for (std::uint8_t byte : fio) std::printf(" %02X", byte);
    std::printf("\n");

    // A parte que interessa: decodificar e usar os campos como variáveis comuns.
    hidl::Operandos op;
    if (!hidl::Operandos::decode(fio, sizeof fio, op)) return 1;

    hidl::Resultado r;
    r.soma = op.a + op.b;
    r.diferenca = op.a - op.b;
    std::uint8_t saida[hidl::Resultado::kSizeBytes];
    r.encode(saida, sizeof saida);

    std::printf("a = %d, b = %d\n", op.a, op.b);
    std::printf("soma = %d, diferenca = %d\n", r.soma, r.diferenca);
    std::printf("pacote Resultado  :");
    for (std::uint8_t byte : saida) std::printf(" %02X", byte);
    std::printf("\n");
    return 0;
}
