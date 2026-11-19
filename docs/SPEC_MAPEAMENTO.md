# Especificação de mapeamento contrato → C++ (MVP)

Este documento é a referência dos back-ends. O código gerado é uma implementação
dele, não a definição dele. Os testes de `tests/test_cpp_backend.py` comparam o C++
gerado com uma referência independente escrita a partir desta especificação.

## 1. Gramática

```
contrato := pacote*
pacote   := "packet" IDENT [ "endian" IDENT ] "{" campo* "}"
campo    := IDENT ":" IDENT ";"
```
Comentários: `// ...` e `# ...` até o fim da linha.

## 2. Tipos do MVP

| Tipo | Significado | Largura |
|---|---|---|
| `bool` | 1 bit (0 ou 1) | 1 |
| `uintN` | inteiro sem sinal | 1 ≤ N ≤ 64 |
| `intN` | inteiro com sinal, complemento de dois | 2 ≤ N ≤ 64 |

Fora do MVP: structs aninhados, arrays, campos condicionais, ponto flutuante.

## 3. Layout de bits

- O pacote é uma sequência de bits. **O bit 0 é o MSB do byte 0** (ordem de rede).
- Os campos ficam na ordem de declaração, sem padding. `offset` do primeiro campo é 0
  e cada campo começa onde o anterior terminou.
- O tamanho total deve ser múltiplo de 8 bits. O compilador não insere padding:
  se precisar, declare um campo de preenchimento.

## 4. Endianness (diretiva `endian`)

- `big` (padrão): o campo ocupa o intervalo de bits `[offset, offset+largura)`, com o
  MSB do valor no primeiro bit do intervalo. Aceita larguras e offsets quaisquer.
- `little`: os **bytes** de cada campo são invertidos. Só é permitido se todos os
  campos tiverem largura múltipla de 8; assim todo offset também é múltiplo de 8.
  A ordem dos campos no pacote não muda.

## 5. Mapeamento para C++

| Contrato | Tipo C++ |
|---|---|
| `bool` | `bool` |
| `uintN` | `std::uint8_t` / `16` / `32` / `64_t` (menor que comporta N) |
| `intN` | `std::int8_t` / `16` / `32` / `64_t` (menor que comporta N) |

- Cada pacote vira uma `struct` com os campos na ordem do contrato, inicializados com zero,
  `static constexpr std::size_t kSizeBytes`, `static bool decode(buf, len, out)` e
  `bool encode(buf, len) const`.
- `decode`/`encode` retornam `false` se `len < kSizeBytes`, sem tocar a saída.
- `decode` de `intN` faz extensão de sinal a partir do bit N−1.
- `encode` zera `kSizeBytes` bytes antes de escrever e grava os N bits menos significativos
  do valor (valor fora da faixa é truncado, como em um cast C).

## 6. Runtime C++ (`hidl/runtime.hpp`)

As regras das seções 3 a 5 (posição dos bits, endianness, extensão de sinal, truncamento) são
implementadas **uma única vez**, em `src/hidl/runtime/hidl/runtime.hpp`: um cabeçalho escrito à
mão, C++11, independente de contrato. O código gerado não repete essa lógica; só chama:

| Função | Efeito |
|---|---|
| `rt::read_be<T, Off, W>(buf)` / `rt::write_be<T, Off, W>(buf, v)` | campo de W bits no bit Off, big-endian |
| `rt::read_le<T, Off, W>(buf)` / `rt::write_le<T, Off, W>(buf, v)` | campo alinhado em byte, little-endian |

- `Off`, `W` e `T` são argumentos de template: tudo é resolvido em tempo de compilação.
  Campos alinhados em byte usam leitura por byte; os demais, um laço bit a bit que o
  compilador desenrola.
- Combinações inválidas não compilam: `W` fora de 1..64, `T` menor que `W`, `T` não inteiro,
  e `read_le`/`write_le` em campo não alinhado em byte.
- `read_*` de tipo com sinal estende o sinal a partir do bit W−1; `write_*` grava os W bits
  menos significativos (seção 5).
- **Versão (ABI):** o runtime define `HIDL_RUNTIME_ABI` e todo `.hpp` gerado contém
  `static_assert(HIDL_RUNTIME_ABI == N, ...)`. Mudar a semântica das funções acima exige
  incrementar esse número (em `runtime.hpp` e em `backends/cpp.RUNTIME_ABI`); um `.hpp`
  gerado por versão antiga passa a falhar na compilação em vez de divergir em silêncio.
- **Distribuição:** `hidl compile --cpp saida.hpp` grava também `hidl/runtime.hpp` ao lado da
  saída (compile com `-I<diretório da saída>`). Com `--standalone` o runtime é embutido no
  `.hpp`; o runtime tem include guard, então os dois modos podem conviver no mesmo programa.

A suíte `tests/test_runtime.py` valida o runtime contra a lógica bit a bit original; qualquer
back-end futuro (por exemplo, Verilog) deve ser validado contra esta mesma especificação.

## 7. Nomes reservados

Campos e pacotes não podem usar palavras-chave do contrato, de C++ ou de Verilog, as portas
do módulo Verilog (`clk rst_n in_valid in_sof in_data out_valid`) nem `decode`/`encode`.
Nomes de pacote também não podem ser `rt` (namespace do runtime C++, seção 6).
A lista está em `semantic.RESERVED` / `semantic.RESERVED_PACKET`.
