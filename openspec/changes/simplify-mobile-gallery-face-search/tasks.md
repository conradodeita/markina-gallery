## 1. Reconciliação e controles da galeria

- [x] 1.1 Reconciliar os trechos conflitantes das changes faciais, roadmap e diretrizes conforme a decisão humana de 21/09/2026; verificar consentimento infantil suficiente sem representação prévia, auditoria direta separada e ausência de sincronização prematura das specs consolidadas.
- [x] 1.2 Mover nome e seleção para faixa compacta abaixo da miniatura; validar seleção/ampliação independentes, nome longo, favoritos, compradas e candidatas com testes do componente compartilhado.
- [x] 1.3 Reorganizar visualizador e stage facial para manter navegação/seleção visíveis numa barra externa abaixo da imagem; validar ausência de interseção dos controles com a fotografia, teclado, zoom/pan, troca de foto e geometria após resize.

## 2. Contrato de consulta por região

- [x] 2.1 Separar origem e campos condicionais da consulta com migration compatível; validar em banco descartável backfill de uploads/regiões legados, preservação de recibos e rejeição de combinações inválidas.
- [x] 2.2 Adaptar API/admissão por região sem consentimento/idade e com evento de auditoria próprio; testar região autorizada, IDOR, região inexistente/revogada, rate limit, capacidade e ausência de recibo fictício.
- [x] 2.3 Adaptar worker, envelopes e lifecycle por origem; testar leitura histórica, execução/cancelamento/expiração, versão divergente, região removida durante espera e preservação de retenção/limpeza. Não sobrescrever alteração preexistente em `facial/purge.py`.
- [x] 2.4 Remover a dependência de representação prévia da disponibilidade, admissão e worker para novas consultas infantis; persistir modalidade/recibo de consentimento e preservar histórico. Testar sucesso com consentimento sem representação, recusa sem aceite explícito/versão válida, revogação por consulta e compatibilidade da revogação de representações históricas.
- [x] 2.5 Verificar regressão de upload adulto e fronteiras da API: ausência de consentimento, versão inválida, sessão/vínculo ausente e arquivo enviado pelo contrato de região devem falhar; fluxo adulto válido deve permanecer inalterado.

## 3. Jornada da cliente

- [x] 3.1 Integrar toque facial ao POST direto com estado de espera imediatamente visível; testar ausência de diálogo/checkboxes, prevenção de toque duplicado, erro retentável e troca de galeria durante resposta pendente.
- [x] 3.2 Coordenar conclusão, fechamento do visualizador e scroll ao topo uma única vez; testar sucesso, ausência de candidatas, falha, polling repetido e restauração de resultado anterior sem salto.
- [x] 3.3 Unificar os dois checkboxes infantis no upload e preservar adulto/menor e aviso; testar opção infantil habilitada com serviço disponível mesmo sem representação, checkbox único inicialmente desmarcado, payload afirmativo versionado e limpeza do aceite ao cancelar/reabrir/trocar tipo.

## 4. Validação integrada

- [x] 4.1 Inspecionar no browser viewports 320px, 360×640, 390×844, paisagem curta e desktop com dados sintéticos; registrar evidência de imagem desobstruída, nome/seleção lado a lado, navegação sempre visível fora da foto e conclusão com retorno ao topo. Não executar biometria real usando os anexos.
- [x] 4.2 Executar testes backend/frontend pertinentes, lint, typecheck e build aplicáveis; registrar comandos/resultados e corrigir regressões causadas pela change.
- [x] 4.3 Validar OpenSpec estrito, diff e compatibilidade com outras changes; registrar limitações e manter sync/archive dependentes de revisão humana.
- [x] 4.4 Corrigir expectativas legadas de consentimento em `test_face_region_search.py` identificadas pelo CI do PR #94; validar busca direta sem idade/consentimento, compatibilidade de transporte sem recibo fictício e preservação de recusas por região/modelo inválido. Evidência: 27 testes aprovados, ruff e OpenSpec estrito aprovados; detalhes em `validation.md`.

## 5. Habilitação operacional infantil

- [ ] 5.1 Preparar inventário de ambiente, portas/subdomínio e plano de impacto zero antes da publicação no servidor; verificar implantação coordenada de API/worker/frontend e disponibilidade infantil por consentimento sem registro de representação, com teste autenticado de escopo autorizado. Registrar versão implantada e evidência sem expor dados pessoais.

## Estado e continuidade

21/09/2026: implementação local concluída conforme decisões humanas: navegação sempre fora da imagem, busca direta por região e regra infantil baseada no consentimento do responsável sem registro prévio de representação. Essas decisões não devem ser perguntadas novamente. Evidências de testes, build e browser em `validation.md`.

O bloqueio anterior por ausência de dados/prova de representação foi removido pela decisão humana explícita. Não pedir cadastro de responsável ou prova administrativa para liberar o novo fluxo. A preparação da task 5.1 está em `deployment.md`; implantação e teste autenticado no servidor permanecem pendentes. Inventário remoto histórico não foi apresentado como estado atual.

As mudanças preexistentes no worktree não pertencem a esta change e foram preservadas fora do commit, inclusive `facial/purge.py` e continuidades de outras changes. Nenhuma imagem dos anexos foi copiada ao repositório ou enviada ao pipeline facial. Sync/archive aguardam revisão humana.

Aplicação e publicação autorizadas em 21/09/2026. Task 1.1: precedência explícita registrada nos documentos e deltas faciais afetados, sem alterar specs consolidadas. O proprietário autorizou expressamente **push + PR para develop e depois parar** (CI dispara em PR ou push para develop). Após esses dois passos, aguardar o proprietário informar CI verde; não consultar/avançar CI, merge, aprovação do ambiente ou deploy automaticamente.
