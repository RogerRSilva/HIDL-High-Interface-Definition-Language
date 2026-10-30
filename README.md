# HIDL — Análise semântica (recorte)

Contém apenas a etapa **AST → IR**: valida o contrato e calcula os offsets dos campos.
Não depende do parser nem de bibliotecas externas (só `pytest` para os testes).

```
src/hidl/ast.py        entrada: PacketDecl / FieldDecl (o que o parser produz)
src/hidl/semantic.py   build_ir(decls) -> list[IRPacket]  (validações + offsets)
src/hidl/ir.py         saída: IRPacket / IRField (imutáveis)
src/hidl/errors.py     Diagnostic / ContractError (um ou vários erros, com linha:coluna)
tests/test_semantic.py 55 testes; montam a AST na mão, sem passar pelo parser
```

```bash
pip install pytest
pytest            # 55 passed
```

## Regras verificadas por `build_ir`

| Regra | Mensagem (trecho) |
|---|---|
| Nome de pacote único | `pacote 'X' já declarado` |
| Nome de campo único dentro do pacote | `campo 'x' já declarado` |
| Pacote com pelo menos um campo | `não tem campos` |
| Nomes não reservados (`packet`, `endian`, palavras de C++ e Verilog, portas `clk rst_n in_valid in_sof in_data out_valid`, `decode`, `encode`) | `é palavra reservada` |
| Tipo ∈ `bool`, `uintN`, `intN` (sem zeros à esquerda) | `tipo desconhecido` |
| 1 ≤ N ≤ 64 | `excede o máximo de 64 bits` |
| `int1` proibido (use `bool`/`uint1`) | `int1 não é suportado` |
| `endian` ∈ `big` (padrão), `little` | `endianness inválida` |
| `endian little`: todo campo com largura múltipla de 8 | `…little-endian, todos os campos devem ter largura múltipla de 8` |
| Tamanho total do pacote múltiplo de 8 bits | `o tamanho total deve ser múltiplo de 8` |

Comportamento: todos os erros são coletados e levantados juntos num único `ContractError`
(cada `Diagnostic` traz `line`/`column`). Se não houver erros, devolve a IR com `offset`
(em bits, a partir do MSB do primeiro byte) já calculado para cada campo.

## Uso

```python
from hidl.ast import FieldDecl, PacketDecl
from hidl.semantic import build_ir

p = PacketDecl("Telemetria", None, (0, 0),
               [FieldDecl("id", "uint16", 2, 5), FieldDecl("velocidade", "uint32", 3, 5)], 1, 8)
(ir,) = build_ir([p])
print(ir.total_bytes, [(f.name, f.offset, f.width) for f in ir.fields])
# 6 [('id', 0, 16), ('velocidade', 16, 32)]
```
