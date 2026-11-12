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

## 6. Nomes reservados

Campos e pacotes não podem usar palavras-chave do contrato, de C++ ou de Verilog, as portas
do módulo Verilog (`clk rst_n in_valid in_sof in_data out_valid`) nem `decode`/`encode`.
A lista está em `semantic.RESERVED`.
