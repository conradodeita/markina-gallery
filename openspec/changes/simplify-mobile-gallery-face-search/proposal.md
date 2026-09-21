## Why

Os anexos 01–03 de 21/09/2026 mostram controles sobre as miniaturas e navegação ampliada fora da área visível no celular. A busca por um rosto já indexado exige hoje o mesmo diálogo do envio de uma referência, interrompendo a procura e deixando os resultados longe da posição atual da cliente.

## What Changes

- Colocar nome do arquivo e botão de seleção menores, lado a lado, abaixo da fotografia; preservar duas colunas no mobile, seleção explícita e acessibilidade.
- Manter `Anterior`, `Próxima` e seleção sempre visíveis em uma barra abaixo e fora da fotografia, inclusive com regiões faciais e zoom habilitados; nenhum desses controles pode sobrepor a imagem.
- Iniciar a busca ao tocar em uma região facial autorizada, sem diálogo nem checkboxes, com estado imediato `Aguarde, procurando fotos…` e progresso real quando disponível.
- Ao concluir a busca iniciada por toque, fechar a ampliação e levar a cliente ao topo da página para percorrer as possibilidades e selecionar manualmente.
- Preservar o consentimento no envio de foto. Conforme esclarecimento humano, manter adulto/menor e reunir as duas confirmações infantis em um único checkbox inicialmente desmarcado: `Sou pai, mãe ou responsável legal e autorizo a busca de fotos desta criança ou adolescente nesta galeria.` O aviso adjacente continua explicando o tratamento temporário da imagem e biometria.
- Separar no backend e na auditoria consulta por região e envio consentido; nunca fabricar aceite ou declarar um rosto adulto automaticamente.
- Liberar a busca infantil no contrato do servidor com base apenas no consentimento específico da cliente que se declara responsável no checkbox único, sem cadastro prévio, comprovação documental ou registro administrativo de representação. Registrar aceite versionado, cliente, galeria e instante, preservando revogação e exclusão.

## Capabilities

### New Capabilities

- `privacy-biometric/direct-region-search-experience`: interação direta com rosto indexado, contrato próprio de admissão/auditoria, progresso, retorno ao topo e consentimento único infantil no upload. Complementa capabilities faciais ainda presentes somente em changes ativas.

### Modified Capabilities

- `gallery-visualization-and-watermark-controls`: controles comerciais externos à miniatura e navegação ampliada visível no mobile.

## Impact

- Frontend compartilhado `gallery-presentation.tsx`, `face-region-viewer.tsx`, `globals.css`, página pública, `facial-search-panel.tsx`, cliente HTTP e testes.
- API, schema de consulta, `facial/search.py`, worker e auditoria: o contrato atual exige `consent_version` e `subject_declaration` para ambas as origens. Pode exigir migration aditiva compatível para representar consulta por região sem consentimento fictício.
- Esta proposta substitui pontualmente a exigência de diálogo por região e a posição dos controles de `evolve-highres-facial-pipeline`, a decisão de dois checkboxes de `clarify-facial-consent-and-mobile-dialog` e a exigência de representação previamente comprovada para novas consultas infantis de `integrate-private-facial-filter` e `productionize-facial-search`. A decisão humana explícita de 21/09/2026 prevalece sobre essa exigência anterior; preservam-se os demais requisitos.
- A disponibilidade infantil no servidor deixará de depender de registro de representação, mantendo autenticação, vínculo, consentimento específico, disponibilidade técnica e retenção. A autorização para essa regra foi recebida; sua publicação no servidor precisa do inventário e plano de impacto zero exigidos pelo projeto. Nenhuma configuração ou ambiente é alterado nesta revisão de planejamento.

## Non-goals

Alterar detecção, modelos, indexação, limiares, retenção, permissões comerciais, marca-d’água ou seleção automática; inferir idade; habilitar produção; executar deploy ou sincronizar/arquivar specs sem revisão.
