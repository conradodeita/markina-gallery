# Validação e continuidade

## Continuação da integração na `main` atual — 18/10/2026

Esta seção registra a retomada isolada do trabalho sobre `origin/main` (`ffea8c4`), que já continha mudanças posteriores na área financeira. Ela complementa as evidências abaixo, produzidas no checkout anterior, e prevalece para os resultados do estado atual desta branch.

- Mantidos os estados financeiros `verifying`, `exception` e `hold`, metadados de adquirente/cartão e o fluxo de download das fotos compradas introduzidos na `main`. O cartão mantém texto explícito de que a confirmação de cartão não usa decisão manual de PIX. O acesso ao download continua condicionado a pedido confirmado, acervo existente e galeria disponível.
- A consulta de pagamentos e a prévia do pedido permanecem no tenant administrativo autenticado. O CSV usa o mesmo escopo de tenant e filtros da lista. A projeção de pagamentos agrupados recebeu o `tenant_id` exigido pela versão atual de `payment_scopes`.
- `pytest tests/test_payment_operations_redesign.py tests/test_payment_status_visual_groups.py -q`: **13 passaram**, com 19 warnings de depreciação/SQLAlchemy do harness existente.
- `pytest tests/test_derived_galleries.py -k 'admin_payment_dashboard or admin_confirms_payment_communication_once or admin_lists_and_refuses_payment_communication_without_confirming_order or payment_communication_contracts_enforce_role_and_gallery_owner or admin_sees_pending_order_snapshots_without_confirming_it or private_media_payment_correction_and_reopening_contracts_start_missing' -q`: **8 passaram, 88 descartados**. Cobrem contratos já existentes de pedido, PIX, pagamentos e reabertura.
- `pytest tests/test_provider_confirmation.py -k admin_payment_queue_identifica_metodo_sem_duplicar_receita -q`: **1 passou, 16 descartados**. Preserva identificação do cartão, receita consolidada sem duplicidade e estado de entrega após confirmação do adquirente.
- Frontend: Vitest focado em pagamentos, fotos, redesign, retirada de Estatísticas e navegação: **26 passaram em 5 arquivos**. A suíte completa `npm test -- --pool=threads --maxWorkers=1`: **562 passaram em 63 arquivos**. `tsc --noEmit`, ESLint dirigido e `npm run build` passaram; rota `/admin/payments` foi gerada e `/admin/statistics` não aparece no build.
- `ruff check` dos arquivos backend alterados, `python -m py_compile`, `git diff --check` e `openspec validate modernize-sales-payments-and-retire-statistics --strict`: aprovados. O lint frontend focado não relatou avisos; lint completo do repositório terminou sem erros e com 34 warnings distribuídos pelos demais arquivos.
- Playwright/Edge headless, somente em localhost, APIs e acervo sintéticos: **6 combinações aprovadas**, em 390/768/1440 px e tema claro/escuro. Foram geradas 18 capturas (listagem, detalhes e lightbox) em `%TEMP%/sales-visual-qa-current`; `report.json` registra os seis resultados. O teste checou overflow horizontal, filtros, CSV, histórico vazio, rota de Estatísticas 404, carregamento de imagem sob demanda, navegação de lightbox, foco, teclado, fechamento e restauração de foco/scroll. Nenhuma decisão ou mensagem real foi executada.
- O script de QA passou a usar `localhost` e a simular `/api/auth/destination`, conforme o contrato atual do `SessionBoundary`. Nenhuma configuração do Next.js ou autenticação da aplicação foi alterada para acomodar o teste. O proxy local da marca/favicon não tinha backend na porta 8000; isso não interrompeu os cenários nem alterou os dados simulados.
- A dependência temporária Playwright 1.61.0 foi instalada em `%TEMP%`, fora do repositório. `npm ci` não alterou o lockfile e informou 11 advisories no conjunto de dependências existente (10 high, 1 critical); nenhuma atualização de dependências foi aplicada nesta change.
- PR de coordenação do lock entre releases API/web: [#222](https://github.com/conradodeita/markina-gallery/pull/222), merge commit `4e969cd247f071d157bc4a1245e3b3262a031d9b`; backend, frontend, Gemma, OpenSpec, gitleaks e política de inventário passaram. O fluxo de release existente agora serializa ambos os caminhos, mas isso não substitui o inventário específico do SHA desta página.

Capturas representativas da inspeção deste checkpoint estão nos arquivos temporários do host: `payments-1440-light.png`, `details-390-light.png` e `lightbox-390-light.png`, em `%TEMP%/sales-visual-qa-current`. O limite de fidelidade comparativa descrito em `design-qa.md` continua: não há uma captura anterior independente, em viewport equivalente, para comparação lado a lado.

## Consulta e CSV

- Banco SQLite sintético isolado em diretório ignorado; DATABASE_URL definida somente no processo dos testes. Nenhum banco operacional acessado.
- `pytest tests/test_payment_operations_redesign.py tests/test_payment_status_visual_groups.py -q`: 10 passaram (97,48 s). Cobertura de prioridade, cursor, filtros, CSV completo, quatro colunas, cotação vs total real, confirmação UTC convertida para São Paulo, vazio, autorização e fórmulas. Três warnings de depreciação preexistentes (Starlette/FastAPI).
- `ruff check backend/app/payment_export.py backend/app/main.py`: aprovado.
- Projeção compartilhada preserva fórmula/ordem existentes; escopos PIX trocados por consultas em lote para evitar N+1 em exportações.

## Inventário de Estatísticas

Exclusivos: frontend/app/admin/statistics/page.tsx e page.test.tsx; quatro handlers `/admin/statistics*`, helpers statistics_data/statistics_txt e dois testes específicos de test_derived_galleries.py; CSS stat-cards, revenue-chart, chart-column, statistics-pagination; item no menu.

Compartilhados a preservar: `.photo-list` (galeria da cliente e pedidos de galeria), `.filter-grid`, UI Kit, `operational_galleries_for_client`, PlainTextResponse, tabelas/pedidos/snapshots, indicadores de Vendas e Visão Geral, bibliotecas React/Next. Busca não encontrou biblioteca ou schema persistente exclusivo da página. Artefatos históricos OpenSpec permanecem como registro e são supersedidos por esta change.

## Checkpoint final de integração

- Backend com SQLite sintético isolado, `DATABASE_URL=sqlite:///./.codex-tmp/sales-integration-tests.db` somente no processo: `pytest tests/test_payment_operations_redesign.py tests/test_payment_status_visual_groups.py tests/test_order_delivery.py tests/test_order_delivery_concurrency.py tests/test_unified_checkout.py -q`: **39 passaram, 5 pulados**, 273,56 s. Os pulados requerem PostgreSQL dedicado para locks; não são considerados aprovados. Três warnings de depreciação preexistentes.
- `ruff check app/main.py app/payment_export.py tests/test_payment_operations_redesign.py tests/test_derived_galleries.py`: aprovado.
- Frontend, checkpoint final após correção do foco: `npm test -- --pool=threads --maxWorkers=1 app/admin/payments app/admin/admin-navigation.test.tsx app/admin/retirement.test.ts app/admin/page.test.tsx app/admin/galleries/orders.test.tsx`: **45 passaram em 9 arquivos**, 26,50 s. A execução focada após correção tinha 35 aprovados; são subconjuntos repetidos, não somar.
- `npx tsc --noEmit`: aprovado. `npm run lint`: zero erros e 25 warnings preexistentes fora do escopo. ESLint dirigido aos pagamentos/retirement/script QA: aprovado.
- `npm run build`: aprovado, inclusive TypeScript e geração de páginas; rota statistics ausente. Primeiro build encontrou tipos gerados dev referenciando página retirada; somente `frontend/.next/dev/types` foi removido após verificar caminho absoluto, e o build repetido passou. Build repetido novamente após correção de foco passou.
- `openspec validate modernize-sales-payments-and-retire-statistics --strict`: aprovado. `git diff --check` relacionado: aprovado. Revisão incremental contra baseline anterior à task preservou alterações locais não relacionadas.

## QA de navegador

- Product Design substituiu UI UX Designer a pedido do proprietário. Preflight executado: sem contexto salvo. Navegador integrado indisponível por configuração do Work; o proprietário autorizou explicitamente a continuação em Playwright/Edge headless com dados sintéticos.
- `frontend/scripts/payments-visual-qa.cjs`, servidor frontend local 127.0.0.1:3117 e interceptação de todas as APIs: **6 cenários aprovados**, 390/768/1440 × claro/escuro, altura 950, acabamento silver. Sem dados, pagamentos, entregas ou avisos reais.
- 18 capturas e `report.json` em `.codex-tmp/sales-visual-qa/` (ignorado). Conferidos ausência de overflow da página/detalhes, lazy loading após expansão, modal real na top layer, foco contido, apenas prévia ativa, teclado/setas, Escape/botão/backdrop, restauração de foco/scroll/expansão, CSV aplicado sem cursor, uma consulta na seleção, histórico vazio, statistics 404 e nenhum pageerror.
- Falha inicial de foco: Shift+Tab saía do primeiro controle do dialog para chrome do navegador. Corrigido ciclo explícito, teste de regressão e repetidos testes/build/matriz com aprovação. Falha subsequente apenas no localizador exato de Exibir no script, corrigido sem mudar aplicação.
- Capturas inspecionadas em mobile claro/escuro, desktop claro, detalhes desktop escuro/mobile e lightbox. Imagens são sintéticas para validar geometria/carga, não conteúdo fotográfico real.

## Entrega e limites restantes

- Relatório A–H: `RELATORIO_IMPLEMENTACAO_VENDAS_PAGAMENTOS.md`. `design-qa.md` registra inspeção e bloqueio de comparação de fidelidade por ausência de referência visual anterior/independente normalizada. QA funcional local passou; aceite visual humano permanece necessário.
- Cinco testes de concorrência PostgreSQL não executados; não validado acervo operacional autenticado, Oracle, canais externos reais ou abertura manual em Excel. Formato/escaping/BOM testados automaticamente.
- Consulta completa em memória herdada, sem benchmark de carga; não afirmar limite ilimitado ou consumo constante. Isolamento preserva arquitetura atual de fotógrafo único; multitenant separado não implementado.
- Nenhum deploy, migration, alteração de secrets/infra ou banco operacional. Testes usaram somente bancos sintéticos isolados. Não houve commit/push; specs principais não sincronizadas e change não arquivada, aguardando revisão humana.

## Publicação em produção — bloqueada

- O proprietário autorizou publicar quando pronto. A validação do alvo mostrou que esta change precisa enviar código ao frontend e à API: `backend/app/main.py` recebe o novo filtro `priority`, endpoint CSV e endpoint de prévias; a remoção das rotas antigas de Estatísticas também é backend. O procedimento local presente em `scripts/deploy-prod-web.sh` (não rastreado no Git) muta somente o serviço `web`, então um release apenas frontend deixaria a UI incompatível com a API e Estatísticas acessível diretamente.
- Não foi improvisado um deploy de `api`, nem usado o workflow CI amplo que recria `api`, `web` e `worker`. Mudar estratégia de deploy precisa de plano explícito e validação de impacto zero; não se inferiu compatibilidade de uma atualização somente `web`.
- O checkout atual tem 151 entradas locais, na branch `feature/improve-individual-selection-download-and-private-layout`; exige árvore limpa. SHA atual `5774ed7d44e25ae46aca1ba4a6a18a2ac9822bd2` é ancestral de `origin/main` (`b695b2e158b3f4f7b7210b598b9de4bd17d330ad`), mas alterações ainda não commitadas não estão nesse SHA. O runbook `docs/DEPLOY-PROD-WEB.md` e `scripts/deploy-prod-web.sh` existem somente como arquivos locais não rastreados nesta checkout; disponibilidade equivalente no host não foi presumida. Nenhum stash/stage/commit/fetch/SSH/Docker foi feito.
- `scripts/test_deploy_prod_web.sh` e `scripts/test_deploy_prod_web_policy.py` executados localmente: ambos aprovados (`deploy-prod-web shell: ok`, `deploy-prod-web policy: ok`). Estes são testes do escopo web-only, não autorização técnica para deploy multi-serviço.
- Inventário conhecido somente da documentação, não atualizado: host `/opt/markina-gallery`; Compose `markina-gallery` e seis manifestos; Markina nginx anteriormente em `127.0.0.1:8080`; domínio `https://markina.pickyourpic.com.br`; arquivo de ambiente `docker/.env.homolog`, valores nunca consultados/expostos. O runbook descreve possível breve interrupção ao recriar `web`; não afirma zero downtime. Nenhum inventário remoto da execução/SHA ou código específico foi emitido/aprovado.
- Plano para retomada: definir release seguro da API e frontend sem recriar worker/data/cache/proxy ou recursos de terceiros; criar PR com somente os arquivos desta change após revisar os 151 itens pendentes; CI/revisão e SHA correspondente em `origin/main`; gerar inventário read-only no host e confirmar manifestos/configuração/saúde/portas/domínio; apresentar impacto (incluindo interrupção), sequência e rollback ao proprietário e vincular aprovação ao SHA/inventário/código exatos; só então publicar e validar healthchecks e `/healthz`, `/api/health`, `/`.
- PostgreSQL de testes dedicado (porta 55458) não estava acessível e processo local postgres ausente. Cinco casos de concorrência seguem pulados conforme relatado acima.

### Atualização do fluxo de publicação — 18/10/2026

O bloqueio histórico descrito nesta seção foi parcialmente resolvido: o PR #222 passou pelos checks obrigatórios e foi integrado em `main`, adicionando lock compartilhado aos fluxos protegidos existentes para API e web. Portanto, o caminho de publicação não está mais limitado ao script web-only citado como referência histórica. A publicação desta change ainda não foi executada: ela depende de branch/PR próprio com o código validado, inventário read-only do host para o SHA final e confirmação explícita do impacto, sequência, healthchecks e rollback exigidos por `AGENTS.md`. Host, serviços, portas e domínio descritos anteriormente são referências documentais, não inventário atual.

### Execução complementar da suíte backend integral — 18/10/2026

- `pytest -q --tb=short` coletou 1.727 testes. A execução local foi interrompida controladamente em 4%, após permanecer sem progresso observável por aproximadamente 15 minutos; não foi obtido resultado integral e ela não é contabilizada como aprovada nem como falha de teste.
- O teste identificado pelo ponto de interrupção (`test_asset_removal.py::test_public_deletion_preserves_group_and_text_without_acervo[False]`) passou quando executado isoladamente: **1 passou em 15,75 s**. Os testes direcionados da change e as regressões listadas acima permanecem aprovados.
- A suíte backend integral precisa ser avaliada no CI do PR; esta validação local inconclusiva não substitui aquele resultado.

### Reconciliação do gate de release API/web — 18/10/2026

- A primeira execução do CI do PR #223 falhou em `homolog-inventory-policy`: o teste comparava `backend/app/main.py` e `frontend/app/globals.css` com blobs antigos e ainda tratava a página removida de Estatísticas como runtime ativo. O check foi reproduzido localmente; não era uma falha funcional do dashboard.
- A allowlist agora inclui somente os arquivos exatos de runtime, testes e QA deste redesign, reconhece somente a exclusão dos dois arquivos antigos da rota de Estatísticas e rejeita novos caminhos nesse diretório. `scripts/check_prod_app_release_scope.py --base origin/main --target HEAD` aprovou `app_release_ready=true`, critério `somente_api_web`.
- Atualizados os blobs candidatos em `runtime-gates.json` e os hashes compartilhados espelhados em `production-gates.json`. `production_baseline_sha` (`b4f15abd6a71585082758062feba7fcfcc225587`), schema (`20261017_0084`), `maintenance_release.authorized=false` e gates de ativação permanecem inalterados; nenhuma publicação foi autorizada por essa sincronização.
- Regressões locais aprovadas: `test_prod_app_release_scope.py` (8), `test_prod_facial_release_gates.py` (7), `test_classify_prod_release.py` (12), `test_readonly_homolog_inventory_policy.py` (7), política do workflow, testes Bash de release facial/API-web, validação OpenSpec estrita e `git diff --check`. A nova execução de CI no commit atualizado permanece necessária.

### Regressão dos contratos de Estatísticas após o CI — 18/10/2026

- No run CI #39124969564, 1.701 testes backend passaram e 23 foram pulados; três testes falharam porque ainda esperavam endpoints de Estatísticas ativos ou chamavam `admin_statistics`, removida intencionalmente nesta change. Os erros foram 404 esperados para as rotas retiradas e `AttributeError` no teste de isolamento multi-tenant específico do endpoint aposentado.
- Substituídos esses contratos obsoletos por verificação de 404 para as oito rotas históricas (`/admin/statistics`, `report`, `csv-access`, `report.html`, `report.csv`, `filters`, `selected-not-purchased.txt`, `purchased.txt`) e removido somente o teste de agregação daquele endpoint; verificações separadas de resumos, exports e isolamento de pedidos continuam presentes.
- Regressão local após a correção: `pytest tests/test_derived_galleries.py::test_statistics_routes_are_retired tests/test_tenant_lifecycle.py -q`: **13 passaram, 1 pulado**; Ruff nos dois arquivos passou. Novo run integral CI necessário para confirmar a correção.
