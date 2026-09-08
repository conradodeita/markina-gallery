## Why

O fluxo desejado permite que um responsável encontre suas fotos em um acervo coletivo sem visualizar fotos de outras pessoas. Como isso envolve dado biométrico, crianças e processamento em servidor ARM, a viabilidade técnica, jurídica e operacional precisa ser comprovada antes de qualquer liberação ao cliente.

## What Changes

- Executar um spike isolado e anonimizado para avaliar detecção, comparação e busca facial limitada a um único evento.
- Definir consentimento específico, retenção mínima, revisão humana do fotógrafo, revogação e exclusão de dados biométricos.
- Medir compatibilidade ARM, licença comercial, precisão, latência, uso de disco/memória e risco de falsos positivos/negativos.
- Produzir uma decisão documentada de aprovar, ajustar ou rejeitar a futura integração com galerias derivadas.

## Capabilities

### New Capabilities

- `privacy-biometric/private-facial-discovery-spike`: gate de avaliação segura para descoberta facial privada por evento.

### Modified Capabilities

<!-- Nenhuma especificação principal existente cobre este comportamento ainda. -->

## Impact

- Pesquisa técnica controlada; nenhum dado real de criança, galeria coletiva pública ou reconhecimento facial para clientes será habilitado por esta mudança.
- Possíveis dependências de modelo, biblioteca de visão computacional e armazenamento temporário, todas avaliadas antes de adoção.
- A mudança `add-derived-client-galleries` permanece funcional sem biometria e não depende de sua aprovação para seleção manual.
