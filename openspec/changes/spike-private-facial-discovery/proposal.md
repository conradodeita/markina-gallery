## Why

O fluxo desejado permite que uma cliente já autorizada encontre rapidamente possíveis fotos de interesse dentro da Galeria pública que ela já pode visualizar, sem criar uma segunda galeria na experiência da cliente. Como isso envolve dado biométrico, crianças e processamento em servidor ARM, a viabilidade técnica, jurídica e operacional precisa ser comprovada antes de qualquer liberação ao cliente.

## What Changes

- Executar um spike isolado e anonimizado para avaliar detecção, comparação e busca facial limitada a um único evento.
- Avaliar uma arquitetura de indexação em background no upload, com embeddings versionados por rosto e comparação posterior contra uma referência temporária da cliente.
- Validar a busca facial como filtro da Galeria pública já autorizada: resultados candidatos aparecem destacados na mesma superfície e não criam galeria privada antes da primeira seleção.
- Comparar YuNet + SFace como baseline de licença permissiva com ao menos um candidato voltado a imagens de baixa qualidade, sem incorporar pesos cuja licença comercial não esteja comprovada.
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
- Qualquer acoplamento ao worker, banco, APIs ou frontend exigirá uma change posterior, migrations aditivas e reconciliação explícita com o roadmap após a aprovação do spike.
