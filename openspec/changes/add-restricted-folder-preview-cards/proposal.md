# Proposal

## Why

No painel administrativo, as pastas restritas aparecem como linhas de texto, embora as pastas comuns já tenham uma prévia clicável. A distinção entre os dois grupos de pastas também não está explícita nos títulos, dificultando localizar o acervo correto.

## What Changes

- Mostrar uma prévia protegida clicável em cada pasta restrita dentro do `Acervo da cliente`, com nome, contagem e estado, abrindo ou recolhendo a pasta pelo mesmo botão.
- Identificar a lista do Acervo como `Pastas restritas ao cliente` e o card de resumo das pastas comuns como `Pastas Públicas`.
- Manter um estado textual acessível para pastas ainda sem prévia e preservar a abertura sem escrita ou processamento novo.
- Acrescentar busca por nome ou telefone no resumo da galeria para filtrar suas clientes vinculadas e corrigir a busca geral para considerar vínculos da galeria única, mantendo sua função de localizar galerias.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: diferenciar visualmente pastas comuns e restritas no painel, permitir abrir a restrita pela prévia protegida e localizar clientes vinculadas na galeria correta.

## Impact

Listagem administrativa de pastas restritas, cards do Acervo, resumo da galeria, busca geral de galerias, estilos e testes correspondentes. Sem alteração de público, autorização de cliente, arquivo original, configuração de processamento ou dados persistidos.
