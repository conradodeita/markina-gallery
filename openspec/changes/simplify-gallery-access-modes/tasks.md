# Tasks

## 1. Base e validação administrativa

- [x] 1.1 Integrar a base documental do PR #107 e conferir branch/diff sem incluir alterações não relacionadas; verificar histórico e lista de arquivos do PR de implementação.
- [x] 1.2 Restringir criação e PATCH explícito de modo a `standard|invite_only`, preservando o padrão `invite_only`, modelo/constraint e guardas legadas; verificar testes de criação dos dois modos, rejeição 422 sem escrita do terceiro e PATCH de outro campo preservando `collective_protected`.
- [x] 1.3 Verificar os contratos de entrada e audiência: nova cliente por link Padrão, link geral sem autorização no convite individual, cliente já vinculada, pastas exclusivas negadas a outra cliente e grade legada negada; acrescentar somente a cobertura ausente e registrar resultados de regressão dirigida.

## 2. Editor e documentação

- [x] 2.1 Exibir somente dois modos e explicações previstas no design; preservar registro legado em salvamento sem escolha e informar efeito de substituição explícita; verificar testes frontend de opções, descrições, payload sem modo legado e escolha explícita sem troca silenciosa.
- [x] 2.2 Atualizar mandato, roadmap e contexto OpenSpec para dois modos operacionais e legado protegido; registrar reconciliação das referências de changes antigas sem reativar propostas conflitantes; verificar busca de referências e comparação com delta specs, mantendo as restrições faciais e de privacidade.

## 3. Configuração de cobrança e seleção externa

- [x] 3.1 Implementar flag e snapshots com migration aditiva e padrão de cobrança obrigatório; validar upgrade em banco isolado, preservação dos registros legados e rejeição de preço zero sem escrita parcial; manter preços progressivos e configurados no modo externo.
- [x] 3.2 Incluir checkbox na etapa 2 e validação frontend/backend de preços positivos quando marcado; validar persistência, troca explícita de modo e ausência de dependência de PIX/preços no modo sem cobrança.
- [x] 3.3 Implementar finalização autenticada/idempotente com congelamento de itens/modo, prazo, autorização e revisão atual; testar sucesso sem PIX, repetição, revisão obsoleta, outra cliente, prazo expirado e seleção adicional independente.
- [x] 3.4 Separar seleção externa de receita, pagamentos e notificações financeiras; apresentar estado próprio em Compras e painel e preservar exportação/entrega/prévias históricas com guarda baseada em snapshot; testar entrega autorizada, negação de pedido pago pendente e alteração posterior da flag sem mutação do histórico.
- [x] 3.5 Adaptar Coleção/Galerias/Carrinho/Compras para ocultar preços e totais externos e exibir confirmação de finalização; separar ações e PIX de carrinho misto; testar fluxos pagos existentes, somente seleção e misto, inclusive falha de PIX sem bloquear seleção externa.

## 4. Mensagem comercial

- [x] 4.1 Incluir mensagem por galeria no payload autorizado da revisão e renderizar texto não vazio no carrinho com quebras de linha; validar mensagem no modo pago/externo, múltiplas galerias, texto vazio, HTML inerte e preservação de snapshots anteriores.

## 5. Integração e entrega

- [x] 5.1 Executar regressão backend de autenticação/acesso/comércio/entrega e suites frontend, lint, typecheck, build/Docker aplicável e OpenSpec estrito; registrar comandos/resultados e revisar diff de autorização, arquivos inesperados e segredos.
- [ ] 5.2 Preparar PR focado e validar CI; publicar em homologação apenas pelo fluxo autorizado com inventário, porta/subdomínio e plano de impacto zero; verificar SHA/healthchecks e manter o ambiente vazio sem limpeza adicional. Parar enquanto Actions estiver rodando, conforme preferência do proprietário.
- [ ] 5.3 Após revisão humana e validação, sincronizar specs e arquivar a change; verificar OpenSpec estrito e evidências de todas as tarefas, sem marcar como executada validação não realizada.

## Evidências e continuidade

- 1.1: PR #107 integrado em develop com checks backend/frontend/OpenSpec/gitleaks aprovados; merge documental `038c26d`, título com `[skip ci]`. Branch de implementação recebeu `origin/develop` sem conflito; planejamento local preservado.
- Implementação em andamento. Testes locais usam DATABASE_URL temporária exclusiva desta change; não usar o banco padrão do checkout nos testes que recriam tabelas.

- 1.2: teste `test_canonical_external_selection_api_admin_export_and_history` passou (SQLite isolado): POST legado rejeitado com 422, PATCH de nome preservou collective_protected e escolha explícita aplicou invite_only. Contratos Pydantic cobrem os dois valores e ausência de modo no PATCH.
- 2.1: suíte gallery-editor passou com 53 testes, incluindo salvamento legado sem access_mode, duas opções, descrições e configuração de cobrança. Typecheck e build Next.js passaram.
- 2.2: mandato/roadmap/contexto receberam decisão substitutiva; roadmap deixou de oferecer três modos; proposal/design de improve-gallery-and-client-data-lifecycle reconciliados como histórico. OpenSpec estrito: 66 itens aprovados.
- 4.1: testes de carrinho passaram para mensagem paga/externa, grupos distintos e HTML inerte; mensagem vazia não renderiza bloco. Snapshot de mensagem e fingerprint preservados; payload agora é emitido por grupo autorizado.
- Checkpoint frontend: suíte completa 334 testes aprovada; depois, testes adicionais de checkbox e histórico externo passaram (54 testes direcionados); lint sem erros e build/typecheck aprovados. Avisos existentes de img/hooks não foram objeto de refatoração.
- Checkpoint backend: acesso/checkouts em SQLite, 26 aprovados/4 pulados; testes de seleção externa/misto, 2 aprovados; API canônica externa, 1 aprovado. Docker backend construído. Validação ampla em andamento.
- Tentativa de combinar suites em PostgreSQL: 23 testes aprovados, mas fixtures antigas de outras suites executam PRAGMA SQLite e falharam antes dos testes. Não alterar essas fixtures fora de escopo; regressão ampla repetida no Docker com SQLite descartável, e concorrência isolada na suite compatível PostgreSQL.
- Primeira regressão ampla revelou downgrade incondicionalmente bloqueado e diferença no payload vazio. Corrigidos: downgrade recusado somente quando houver configuração/histórico externo; finalized_orders é omitido quando vazio, preservando contrato anterior. Suite ampla repetida; nenhuma falha foi ignorada como aprovação.

- 3.1: test_optional_payment_upgrade aprovado em SQLite e PostgreSQL novo descartável: gallery default verdadeiro preservado, novo snapshot/constraint presentes, downgrade recusou modo externo e aceitou estado compatível (sem dados externos). 3 testes dirigidos de migration/retencão aprovados.
- 3.2: checkbox marcado inicialmente, preço zero bloqueado e desmarcado permite salvar sem PIX/preço; testes de editor e API canônica aprovados. Modo externo preserva preços administrativos anteriores e dispensa conversão de preço legado.
- 3.3/3.4: suite unificada PostgreSQL: 22 aprovados, incluindo concorrência de seleção/checkout/pagamento, revisão/idempotência e API externa. API externa prova vínculo, congelamento, histórico sem total, exportação autenticada e entrega. Retenção explícita externa foi testada com arquivos sintéticos locais e mantém status/contabilidade sem confirmar pagamento. Novos testes de mudança com rascunho em validação final; regressão ampla ainda pendente no checkpoint 5.1.

- 3.5: suíte frontend final: 48 arquivos/337 testes aprovados; teste de carrinho misto com PIX indisponível confirma finalização externa independente. Build/typecheck aprovados. Contagem do resumo PIX contém apenas fotos com cobrança; mensagem de sucesso não é duplicada no carrinho misto.
- Teste adicional de troca para modo externo aprovado: descarta apenas rascunho pago editável, recusa endpoint PIX legado, invalida revisão antiga e mantém total da outra galeria paga. Concorrência de finalização externa em PostgreSQL aprovada: duas chamadas com mesma chave retornam um único pedido com dois itens.

- Revisão de base: para não incluir os commits originais do PR documental (que foi squash-merged), criada codex/simplify-gallery-access-modes diretamente em origin/develop=038c26d. A árvore da antiga HEAD era idêntica à base; git switch preservou todas as alterações locais sem stash, reset, checkout destrutivo ou rebase. Histórico do futuro PR conterá somente esta change.
- Regressão ampla Docker/SQLite: 839 aprovados, 16 pulados, 2 falhas de contrato JSON legado. Corrigidas preservando shape anterior: orders_by_status só adiciona not_required quando existe pedido externo; histórico pago omite o campo novo payment_required (somente seleção externa emite false). Revalidação dirigida dessas falhas em andamento. Não registrar a execução anterior como verde.

- Validação final 1.3/5.1: após corrigir os dois contratos legados, `pytest tests/test_unified_checkout.py tests/test_gallery_lifecycle.py -q --tb=short --maxfail=2 -p no:cacheprovider` no Docker/SQLite descartável: 76 aprovados, 5 pulados. As suites de autenticação, acesso assinado, galerias derivadas, audiência de pastas, comércio e entrega passaram na execução ampla; não houve alteração em OTP/convites nem nas guardas de público. Testes existentes de entrada padrão/convite/coletivo e pasta exclusiva foram preservados.
- Frontend final: suíte completa anterior com 337 aprovados; depois do ajuste para dispensar precificação legada no payload externo, `npm test -- app/admin/galleries/gallery-editor.test.tsx app/library` passou com 82 testes e `npx --no-install tsc --noEmit` passou. `npm run lint`: zero erros, 29 avisos (img/hooks/variáveis em testes); nenhuma refatoração fora do escopo.
- Builds finais aprovados: `docker build -t markina-gallery-optional-payment-check:local backend` e `docker build -t markina-gallery-optional-payment-front-check:local frontend`; frontend inclui build Next.js/TypeScript. Primeira chamada usou caminho inexistente docker/backend.Dockerfile e foi corrigida para backend/Dockerfile, sem alteração no repositório.
- `ruff check backend/app backend/tests`: aprovado. `npx --yes @fission-ai/openspec@latest validate --all --strict --no-interactive`: 66 aprovados, zero falhas. `git diff --check`: aprovado. Revisão final sem env/secrets, dados, uploads, caches ou arquivos não relacionados; migration aditiva e guardas de autorização/snapshot revisadas. Spec principal e arquivamento aguardam revisão humana.
- Encerrado somente o PostgreSQL efêmero `markina-gallery-optional-payment-tests`, após conferir label task=simplify-gallery-access-modes e término dos testes. Os bancos sintéticos dessa execução foram descartados pelo --rm; containers Evolution e dados reais não foram alterados. Homologação não foi modificada nesta implementação local.
