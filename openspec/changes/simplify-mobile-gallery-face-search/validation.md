## Planejamento inicial — histórico de 21/09/2026

- `npx --offline @fission-ai/openspec@1.10.0 validate simplify-mobile-gallery-face-search --strict`: aprovado.
- `npx --offline @fission-ai/openspec@1.10.0 status --change simplify-mobile-gallery-face-search`: 4/4 artefatos completos (proposal, specs, design, tasks). Isso indica planejamento completo, não implementação.
- `git diff --check`: sem erro; avisos LF/CRLF dizem respeito a documentos preexistentes de outras changes.
- Conferência do status: somente o diretório desta change foi acrescentado nesta execução. Arquivo backend e documentos preexistentes permanecem modificados pelo trabalho anterior.
- Revisão dos deltas: dois contratos, com cenários para layout mobile, interação direta, isolamento, erro, auditoria, retorno ao topo e checkbox infantil único.
- Não foram executados testes do produto, build, migration, processamento facial real, deploy ou edição de código. Todos os itens de implementação permanecem pendentes.

## Decisões humanas recebidas

O pedido contempla seleção menor ao lado do nome, navegação ampliada visível, busca por toque sem popup/checkbox, espera visível e retorno ao topo. No envio de foto, a resposta de esclarecimento foi: “Sim, unificar os dois checkboxes para menores”, preservando escolha adulto/menor. Os anexos são evidência da interface, não autorização para extração facial nem prova de representação.

## Limite operacional inicial — supersedido

O anexo 03 mostra opção infantil indisponível. No código atual, `search_availability` calcula essa disponibilidade pela representação vigente para cliente/galeria/versão. A ativação real está registrada na task 5.1 como pendente de escopo e evidência, separada do trabalho local. Não foi alterada configuração de nenhum ambiente.

## Implementação autorizada — 21/09/2026

O proprietário posteriormente autorizou a regra infantil baseada apenas no consentimento do responsável, sem representação previamente registrada. Esse limite do planejamento foi supersedido. Implementados nome/seleção compactos sob a miniatura; navegação visível fora da imagem; consulta por região sem diálogo/checkbox; espera imediata; sucesso fecha ampliação e volta ao topo uma vez. Upload conserva escolha adulto/menor, com único aceite infantil que reúne declaração de responsável e consentimento. Recibos e revogação históricos são preservados.

Nenhum anexo foi processado como biometria. Testes usaram imagens, vetores e respostas sintéticos. Sem alteração de `.env`, credenciais, infraestrutura, dados remotos ou specs consolidadas.

### Evidências automatizadas

Comandos executados da raiz, salvo frontend (diretório `frontend`). Python/ruff usados de `backend/.venv/Scripts/`.

| Validação | Evidência |
|---|---|
| `npm test -- --maxWorkers=2` | 45 arquivos / 327 testes aprovados. A rodada com concorrência padrão teve 326 aprovados e timeout no teste administrativo preexistente `decide no card do editor...`; ele passou isoladamente, sem alteração, e a suíte completa passou com dois workers. |
| `npm test -- app/public-galleries/facial-search-panel.test.tsx app/public-galleries/public-gallery.test.tsx app/gallery-presentation.test.tsx app/face-region-viewer.test.tsx` | 33 testes passaram antes dos quatro cenários adicionais de erro/retentativa/troca de galeria. |
| `npm test -- app/public-galleries/public-gallery.test.tsx` | 15 testes passaram, incluindo os quatro cenários adicionais. |
| `npm run lint` | Zero erros; 27 avisos existentes de imagens/variáveis. |
| `npx tsc --noEmit` e `npm run build` | Aprovados; build Next.js e geração de rotas completos. |
| `ruff check backend/app backend/tests backend/migrations/versions/20260921_0060_facial_search_authorization.py` | Aprovado. Varredura adicional de todas as migrations encontrou 14 problemas de imports em arquivos antigos não alterados; esse diretório não integra o gate ruff do CI. |
| `pytest backend/tests/test_direct_region_search.py -q` | 4 cenários integrados passaram: região sem arquivo/consentimento, invalidação antes de executar, menor sem representação e cancelamento. Inclui rejeição de cliente/galeria incorretos e modelo obsoleto. |
| `pytest backend/tests/test_direct_region_search.py -k contract -q` | 1 teste passou: UUID mínimo aceito, campo de arquivo rejeitado. |
| `pytest backend/tests/test_direct_region_search.py backend/tests/test_facial_http.py backend/tests/test_facial_search.py backend/tests/test_facial_models.py -q` | 23 testes passaram na rodada de integração; teste de contrato acrescentado depois e validado separadamente. |
| `pytest backend/tests/test_facial_search_worker.py backend/tests/test_facial_legal_representation.py backend/tests/test_facial_purge.py backend/tests/test_facial_security.py backend/tests/test_facial_integration.py backend/tests/test_highres_migration.py -q` | 28 testes passaram em 278,27 s. Concorrência, persistência, isolamento, limites, cancelamento, expiração, notificações, limpeza e representações legadas. |
| `pytest backend/tests/test_highres_pipeline.py -k upload_index_media_region_query_and_purge_integrated -q` | 1 teste passou: índice → região → consulta direta → resultado/notificação → purge. Primeira execução revelou `consent_version=None` no envelope de notificação; corrigido usando a versão do aviso para consulta direta. |
| `pytest backend/tests/test_facial_search_authorization_migration.py -q` | 1 teste passou em 48 s: upgrade/backfill, preservação de recibos, origem legada desconhecida, constraints e downgrade protegido. Banco SQLite descartável. |
| `npx --offline @fission-ai/openspec@1.10.0 validate --strict --all` | 57 itens aprovados. |
| `git diff --check` | Sem erros; avisos de normalização LF/CRLF apenas. Diff revisado para preservar estritamente o trabalho preexistente. |

Proteções de frontend: restauração atrasada não substitui busca nova; polling antigo é ignorado após cleanup; resposta após troca de galeria não escreve storage nem provoca scroll. Retry-After impede tentativa prematura. Seleção manual, favoritos e estados comerciais seguem testes existentes do componente compartilhado.

### Browser com build de produção e dados sintéticos

Chrome headless via Playwright, serviço local exclusivo em `127.0.0.1:3100`, respostas HTTP sintéticas interceptadas. Conferidos: ausência de overflow horizontal, seleção abaixo da imagem, nome ao lado da seleção, fotografia desobstruída, navegação externa visível, busca direta e scroll ao topo. Também aprovados zoom, arraste, redimensionamento e navegação por botão/teclado. Screenshots inspecionados em 320px e paisagem. Área de toque de 44px preservada com cápsula visual menor.

| Viewport | Stage (y/altura) | Navegação (y/altura) | Resultado |
|---|---|---|---|
| 320×640 | 165 / 322 | 583 / 44 | Aprovado |
| 360×640 | 117 / 370 | 583 / 44 | Aprovado |
| 390×844 | 117 / 574 | 787 / 44 | Aprovado |
| 740×360 | 125 / 166 | 295 / 44 | Aprovado |
| 1440×900 | 133 / 630 | 843 / 44 | Aprovado |

Harness, screenshots e logs locais em `.codex-tmp/mobile-facial-*`, excluídos do Git. Evidência geométrica acima preservada para continuidade sem depender desses artefatos temporários.

### Limites e continuidade

Validação Windows/SQLite e browser sintético não equivale a homologação Linux/PostgreSQL/autenticada. A suíte completa backend será executada pelo CI. Sem deploy, migration operacional ou processamento real. Task 5.1 pendente; ver `deployment.md`. Publicar branch e PR, então parar até o proprietário informar CI verde. Não consultar CI automaticamente nem efetuar merge. Sync/archive dependem de revisão humana.
