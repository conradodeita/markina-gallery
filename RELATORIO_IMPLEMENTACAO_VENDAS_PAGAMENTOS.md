# Relatório de implementação — Vendas e pagamentos

Data da execução: 17/10/2026, no ambiente local informado pelo proprietário.

Change: `openspec/changes/modernize-sales-payments-and-retire-statistics/`.

Escopo autorizado: prompt de implementação anexado pelo proprietário, que substituiu a etapa anterior de documentação sem alterações. A implementação foi continuada sobre o workspace existente. Product Design foi utilizado na revisão final, substituindo UI UX Designer conforme solicitado.

## A. Resumo da implementação

- Reorganizada a página `/admin/payments`, mantendo clientes agrupados e pedidos expansíveis, identidade visual, UI Kit e tokens existentes.
- Detalhes distribuídos em Fotografias do pedido, Pagamento e Entrega, com quantidade no resumo e total persistido.
- Selecionar uma sugestão de cliente aplica a consulta imediatamente por clique ou Enter.
- Entrada e limpeza dos filtros usam Pendências prioritárias: pagamentos comunicados e confirmados sem entrega. Todos permanece uma opção distinta.
- Acrescentadas miniaturas de 64 px e ampliação em modal, utilizando derivados existentes e acesso administrativo autenticado por item do pedido.
- Implementada exportação CSV autorizada no servidor, de todos os pedidos correspondentes aos filtros aplicados, com exatamente quatro colunas.
- Aposentada Estatísticas: interface, menu, quatro endpoints e recursos comprovadamente exclusivos removidos. Acesso legado retorna 404.
- Sem migrations, deploy, alterações de secrets ou operações em banco operacional.

## B. Arquivos modificados

Os caminhos abaixo são relativos à raiz do repositório. O workspace já continha alterações de outras tarefas; esta relação descreve somente o incremento desta execução.

### Aplicação

| Situação | Arquivo | Responsabilidade nesta entrega |
|---|---|---|
| Alterado | `frontend/app/admin/payments/page.tsx` | Estrutura da página; filtro prioritário e Todos; aplicação automática de cliente; controle de consultas concorrentes; exportação e feedback; organização dos detalhes. |
| Criado | `frontend/app/admin/payments/payments.module.css` | Layout específico da página e do modal, utilizando tokens existentes. |
| Criado | `frontend/app/admin/payments/order-photos.tsx` | Lista de fotografias, miniaturas lazy, estados de imagem e lightbox com foco, teclado e restauração de contexto. |
| Alterado | `frontend/app/admin/admin-navigation.tsx` | Remoção da entrada Estatísticas. |
| Alterado | `frontend/app/globals.css` | Remoção dos seletores exclusivos de Estatísticas. Tokens e estilos compartilhados permanecem. |
| Alterado | `backend/app/main.py` | Filtro sintético, extração da consulta existente para reutilização, API CSV, prévias por item, escopos PIX em lote e remoção das rotas/helpers exclusivos de Estatísticas. |
| Criado | `backend/app/payment_export.py` | Serialização CSV, cabeçalhos, valores, datas, escaping e neutralização de fórmulas. |
| Removido | `frontend/app/admin/statistics/page.tsx` | Antiga interface de Estatísticas. |

### Testes e documentação

| Situação | Arquivo | Finalidade |
|---|---|---|
| Criado | `backend/tests/test_payment_operations_redesign.py` | Prioridade, CSV completo, autorização, filtros, query count, datas, agrupamento, segurança, derivados e aposentadoria. |
| Alterado | `backend/tests/test_derived_galleries.py` | Removidos somente dois testes exclusivos dos relatórios aposentados. |
| Criado | `frontend/app/admin/payments/redesign.test.tsx` | Busca automática, filtros, exportação, respostas obsoletas e montagem sob demanda. |
| Criado | `frontend/app/admin/payments/order-photos.test.tsx` | Modal, estados de imagem, foco, teclado e scroll. |
| Alterado | `frontend/app/admin/payments/page.test.tsx` | Ajustes dos contratos de teste à busca imediata, marcadores visuais e respostas independentes de fetch. |
| Alterado | `frontend/app/admin/admin-navigation.test.tsx` | Verifica ausência da entrada aposentada. |
| Criado | `frontend/app/admin/retirement.test.ts` | Confirma ausência da antiga página no App Router. |
| Removido | `frontend/app/admin/statistics/page.test.tsx` | Teste exclusivo da interface retirada. |
| Criado | `frontend/scripts/payments-visual-qa.cjs` | QA em Edge headless com APIs interceptadas e dados sintéticos; não envia ações reais. |
| Criados | `openspec/changes/modernize-sales-payments-and-retire-statistics/*` | Proposal, design, delta spec, tasks e evidências. |
| Criados | Este relatório e `design-qa.md` | Entrega técnica e limites da avaliação visual. |

Não foram alterados `payment-actions.tsx`, `order-delivery.tsx`, `removed-history.tsx`, UI Kit, pipeline de geração de mídia ou handlers de decisão financeira/entrega. Eles continuam integrados à página.

## C. Funcionalidades preservadas

### Regras financeiras e operacionais

- Comunicação de PIX continua diferente de confirmação efetiva. O redesign não confirma pagamentos automaticamente.
- `PaymentActions` mantém confirmação manual, pagamento não localizado, nova conferência, correção e confirmação das ações conforme o contrato anterior.
- O escopo de um PIX agrupado continua apresentando e decidindo todos os pedidos do grupo. A consulta passou a obter escopos em lote, reutilizando `payment_scopes`, sem mudar seu conteúdo.
- Correção financeira continua seguindo os handlers existentes, inclusive retorno à conferência, invalidação dos avisos aplicáveis e restrição da entrega.
- `OrderDeliveryForm` mantém validação do link HTTPS do Google Photos, permissões, versão, reenvio explícito/idempotência, remoção e tratamento de conflito/erro.
- Download de fotos compradas continua condicionado à confirmação, galeria disponível e acervo não removido.
- Reaberturas, prazo, recusa, aviso e retry permanecem nos controles existentes.
- Prévia/edição da mensagem global permanece vinculada a Notificações.
- Histórico de acervo excluído mantém seu componente e paginação próprios.

### Pesquisa, filtros, listagem e indicadores

- Busca por nome/telefone; cliente exato; galeria pública; período; situações individuais; composição dos filtros e paginação por cursor preservados.
- Debounce de sugestões de 180 ms, cancelamento, setas, Enter e Escape preservados. Busca livre continua usando Aplicar.
- A seleção automática conserva os filtros efetivamente aplicados. Rascunhos ainda não aplicados não entram silenciosamente na consulta nem no CSV.
- Ordem e prioridade existentes dos grupos/pedidos permanecem. Não foi introduzida outra ordenação.
- As fórmulas de clientes, orçamento das seleções, pedidos comunicados e receita confirmada continuam sendo as da projeção existente. Os valores refletem o escopo consultado.
- Seleções em aberto permanecem disponíveis em Todos, nas condições anteriores: ausência de filtro financeiro e de entrega, além dos demais critérios. Não são pagamentos confirmados nem linhas extras do CSV de pedidos.
- Atualização de resultados conserva os dados e componentes existentes enquanto consulta o servidor; erros de atualização são apresentados sem apagar os registros já carregados.

## D. Melhorias implementadas

### Organização e responsividade

O cabeçalho reúne título e seletor Exibir. A barra aderente de cliente/telefone reúne Aplicar e Exportar CSV. Os critérios adicionais permanecem em Mais filtros. Depois aparecem indicadores, mensagem global, reaberturas quando existentes, clientes/pedidos, paginação e seleções abertas quando aplicáveis.

Cada pedido resume galeria, identificação, quantidade real de itens, total e situação. Ao expandir, apresenta fatos e três áreas explícitas. Desktop usa duas colunas para fotografias e operação; até 900 px, os detalhes ficam em uma coluna. Até 600 px, cabeçalho e ações se acomodam à largura disponível. Os demais breakpoints globais existentes continuam válidos.

Mantidos `MarkinaButton`, `MetricCard`, `StatusBadge`, `SystemState`, tipografia e variáveis `--mk-*`/`--payment-status-*`. Não foi instalada biblioteca visual nem criado tema paralelo.

### Filtro padrão e busca

`priority` é um parâmetro de consulta, sem novo status persistido. Seleciona apenas `reported` e `confirmed_undelivered`. Limpar remove cliente, galeria, datas e cursor, restaura esse parâmetro e recarrega. Todos omite a restrição financeira. A API sem filtro mantém compatibilidade com seus consumidores anteriores.

Escolher sugestão inicia uma consulta exata por `client_id`, mantendo filtros aplicados. `AbortController` impede que resposta antiga substitua a consulta atual. O teste verifica uma consulta por escolha tanto em clique quanto em Enter.

### Fotografias e lightbox

- Miniaturas visuais de 64 × 64 px com `object-fit: contain`, arquivo e preço por item.
- Imagens montadas somente nos pedidos expandidos e com `loading="lazy"`; recolher desmonta as miniaturas.
- Ausência de URL/derivado apresenta estado indisponível; erro de imagem não aciona original como fallback.
- Ampliação por portal e `<dialog>.showModal()`, na top layer, sobre a interface inteira; fundo escurecido.
- Fechar ×, Escape e clique fora do conteúdo; Anterior/Próxima e setas do teclado, limitadas às fotos do pedido.
- Foco inicial no fechamento, ciclo explícito por Tab/Shift+Tab, retorno ao acionador, bloqueio/restauração do scroll e preservação dos detalhes/filtros.
- Apenas a foto ativa é montada ampliada. Trocar a foto desmonta a imagem anterior; não há preload das demais.

Endpoint: `GET /admin/orders/{order_id}/items/{item_id}/preview?size=thumbnail|preview`. Usa `thumbnail` e `admin_preview` prontos, gerados pelo pipeline existente. O tamanho visual de 64 px não altera a dimensão do derivado existente (thumbnail de até 480 px).

### CSV

Endpoint: `GET /admin/payment-communications/export.csv`.

Cabeçalho exato, nesta ordem:

```text
Nome do cliente;Item/descrição;Total dos itens/pedido;Data e hora
```

- Uma linha por pedido; pedidos do cliente consecutivos; ordem da consulta preservada.
- Descrição: quantidade de itens e galeria pública real/snapshot disponível no pedido.
- Total: `SaleOrder.total_cents`, sem reconstruir a soma por preço presumido.
- Data: `confirmed_at` somente quando o pedido está efetivamente confirmado. Caso contrário, célula vazia. Conversão para `America/Sao_Paulo`, formato `dd/mm/aaaa HH:mm:ss`.
- Todos os pedidos filtrados, independentemente do cursor carregado no navegador.
- UTF-8 com BOM, ponto e vírgula, CRLF, decimal com vírgula e escaping por `csv.writer`.
- Textos não confiáveis iniciados por fórmulas/controles recebem proteção por apóstrofo.
- Nenhuma coluna extra, imagem, telefone ou nome individual de fotografia.
- Arquivo `pick-your-pic-vendas-pagamentos.csv`; botão desabilitado enquanto exporta; feedback de sucesso, erro e vazio (HTTP 204).

## E. Aposentadoria de Estatísticas

Inventário e remoção:

- Página `/admin/statistics`, teste exclusivo e entrada no menu.
- APIs `GET /admin/statistics`, `/admin/statistics/filters`, `/admin/statistics/selected-not-purchased.txt` e `/admin/statistics/purchased.txt`.
- Helpers exclusivos `statistics_data` e `statistics_txt`.
- Dois testes desses relatórios em `test_derived_galleries.py`.
- CSS exclusivo: `.stat-cards`, `.revenue-chart`, `.chart-column` e `.statistics-pagination`, incluindo sua regra responsiva.

A rota de frontend e os quatro endpoints retornaram 404 nos testes. A tabela de rotas do build não inclui Estatísticas.

Preservados: `.photo-list`, `.filter-grid`, UI Kit, helpers operacionais compartilhados, dados/snapshots de clientes e pedidos, indicadores de Vendas e Visão Geral e filas técnicas. Não foi identificado pacote, tabela, migration ou store exclusivamente removível dessa tela. Não se removeu dependência compartilhada.

Referências históricas em documentação/OpenSpec permanecem como registro; a change atual documenta a aposentadoria. Uma busca ampla via Jev encontrou bloqueio de acesso em diretório temporário de outra investigação; buscas direcionadas no código de aplicação e documentação ativa foram utilizadas no inventário.

## F. Testes executados

### Backend

Na pasta `backend`, com `DATABASE_URL` definida apenas no processo para SQLite sintético em `.codex-tmp/sales-integration-tests.db`:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_payment_operations_redesign.py tests/test_payment_status_visual_groups.py tests/test_order_delivery.py tests/test_order_delivery_concurrency.py tests/test_unified_checkout.py -q
.venv/Scripts/ruff.exe check app/main.py app/payment_export.py tests/test_payment_operations_redesign.py tests/test_derived_galleries.py
```

Resultado: **39 passaram, 5 pulados**; Ruff aprovado. Os cinco pulados exigem PostgreSQL dedicado para validar locks concorrentes. A execução levou 273,56 s e apresentou três warnings preexistentes de depreciação FastAPI/Starlette.

Antes do checkpoint completo, foram executadas validações focadas de prioridade/CSV (10 passaram), prévias (1 passou) e aposentadoria (1 passou). Não somar esses números ao checkpoint, pois incluem casos repetidos.

Cobertura relevante: autenticação; combinações/vazio/período inválido; exportação além do cursor; quatro colunas e caracteres especiais; total salvo; confirmação real/fuso; fórmulas; pedidos contíguos por cliente; consultas em lote; bytes dos derivados; item de outro pedido; original proibido; arquivo ausente/acervo removido; regras PIX agrupadas/correção/entrega e notificações existentes.

### Frontend

Na pasta `frontend`:

```powershell
npm test -- --pool=threads --maxWorkers=1 app/admin/payments app/admin/admin-navigation.test.tsx app/admin/retirement.test.ts app/admin/page.test.tsx app/admin/galleries/orders.test.tsx
npx tsc --noEmit
npm run lint
npx eslint app/admin/payments app/admin/retirement.test.ts scripts/payments-visual-qa.cjs
npm run build
```

Resultado do checkpoint final: **45 testes passaram em 9 arquivos** (26,50 s). Diretório de pagamentos após correção de foco: 35 testes aprovados. Typecheck aprovado. Lint completo: zero erros e 25 warnings preexistentes fora do escopo. Lint direcionado dos arquivos da página/script aprovado. Build Next.js 16.4.0 aprovado após a correção de foco.

Falha intermediária de build: tipos gerados do modo dev ainda referenciavam a página removida. Resolvida removendo apenas o cache gerado `frontend/.next/dev/types`, após validar o caminho absoluto; novo build aprovado. Nenhum arquivo fonte foi descartado.

### Navegador e capturas

O navegador integrado estava desativado nas configurações do Work. O proprietário autorizou explicitamente o fallback de QA com Playwright/Edge headless, somente em localhost e dados sintéticos.

```powershell
# PLAYWRIGHT_MODULE aponta para o runtime Playwright já disponível no ambiente.
node scripts/payments-visual-qa.cjs
```

Resultado: **6 cenários aprovados**, larguras 390, 768 e 1440 px × temas claro/escuro, altura de viewport 950 px, acabamento Cinza metálico. Foram geradas 18 capturas (listagem, detalhes e lightbox), além de `report.json`, em `.codex-tmp/sales-visual-qa/` (ignorado pelo Git).

Verificados: ausência de overflow horizontal na página e detalhe; nenhuma imagem antes de expandir; nenhuma ampliação antecipada; uma imagem ativa; modal real; foco contido; setas; Escape, Fechar × e clique externo; retorno de foco/scroll/expansão; CSV com filtros sem cursor; uma consulta na seleção de cliente; histórico vazio; Estatísticas 404; nenhum `pageerror` nos cenários.

Falha intermediária: Shift+Tab escapava do primeiro controle para o chrome do navegador. Corrigido ciclo explícito no modal, acrescentada regressão e repetidas validações unitárias, build e navegador. Outra falha foi apenas o seletor exato de Exibir no script; o localizador foi corrigido e a matriz repetida com aprovação.

Capturas de referência sintéticas (não representam pedidos/imagens reais):

- [Desktop claro](<C:/Users/Conrado/Documents/Photo Delivery/.codex-tmp/sales-visual-qa/payments-1440-light.png>)
- [Detalhes desktop escuro](<C:/Users/Conrado/Documents/Photo Delivery/.codex-tmp/sales-visual-qa/details-1440-dark.png>)
- [Mobile claro](<C:/Users/Conrado/Documents/Photo Delivery/.codex-tmp/sales-visual-qa/payments-390-light.png>)
- [Mobile escuro](<C:/Users/Conrado/Documents/Photo Delivery/.codex-tmp/sales-visual-qa/payments-390-dark.png>)
- [Lightbox mobile](<C:/Users/Conrado/Documents/Photo Delivery/.codex-tmp/sales-visual-qa/lightbox-390-light.png>)

### OpenSpec e revisão incremental

`openspec validate modernize-sales-payments-and-retire-statistics --strict` aprovado. `git diff --check` dos arquivos relacionados aprovado. Alterações comparadas com cópias de baseline anteriores à implementação, sem reverter mudanças preexistentes. Não houve commit, push, sincronização de spec principal nem arquivamento.

## G. Desempenho e segurança

- Sem pipeline novo e sem leitura/fallback de original. Prévias usam arquivos derivados existentes, validação de caminho e associação pedido/item/foto.
- `require_admin` protege CSV e imagens; parâmetros tipados, variantes restritas, indisponibilidade em 404 e headers privados/restritivos (`private, no-store`, `nosniff`). Nenhum caminho de disco é entregue no payload.
- O cache dos derivados gerados em disco é reutilizado; não foi relaxada a política HTTP de proteção para tornar fotos cacheáveis publicamente.
- Miniaturas somente ao expandir e via lazy loading; ampliação apenas da foto corrente. Não há carregamento de imagens no CSV.
- Consulta e exportação compartilham predicados e ordenação. Escopos PIX são resolvidos em lote; teste com 15 clientes verifica menos de 20 instruções SQL, sem consulta por foto/pedido.
- A exportação evita baixar sucessivas páginas para montar CSV no browser. O navegador recebe apenas o arquivo final e libera sua URL temporária.
- O legado já reúne pedidos antes de paginar clientes. A exportação continua materializando os registros filtrados em memória no servidor; não é streaming e seu custo cresce com o resultado. Não foi realizado teste de carga em volume de produção nem medição no Oracle Free Tier. Não se afirma consumo constante ou capacidade ilimitada.
- A autorização preserva a arquitetura atual de fotógrafo único. A fundação multitenant planejada em outra change não foi implementada nem substituída por isolamento fictício.
- Nenhuma credencial, `.env`, schema, container, rede, volume ou recurso remoto foi alterado.

## H. Pendências e limites

1. **Concorrência PostgreSQL:** cinco casos não executados por exigirem banco dedicado; SQLite não valida os locks. Não houve alteração dos handlers de decisão/entrega, mas aprovação desses casos não é presumida.
2. **Ambiente real:** sem validação autenticada de ponta a ponta com acervo operacional, entrega externa, WhatsApp/push, planilha Microsoft Excel instalada ou Oracle. APIs e fluxos foram exercitados em testes isolados; a revisão visual usou fixtures. BOM/formato/escaping foram verificados em código/testes, não pela abertura manual no Excel.
3. **Fidelidade visual:** capturas foram inspecionadas em desktop/mobile e claro/escuro. Não foi fornecido mockup visual independente nem capturada uma referência anterior normalizada para comparação lado a lado; `design-qa.md` registra esse limite. Não se declara equivalência pixel a pixel ou auditoria WCAG completa. Os outros acabamentos do sistema não tiveram matriz visual própria.
4. **Capacidade:** consulta completa em memória herdada; não houve benchmark de carga/Free Tier.
5. **Publicação em produção bloqueada pelo escopo do procedimento local:** esta change altera `backend/app/main.py` e o frontend. O script `deploy-prod-web.sh` presente somente como arquivo local permite mutar `web`; não publica a API. Publicar somente `web` faria o cliente novo chamar `financial_status=priority` ainda desconhecido pelo backend, receber 404 no CSV/prévia e manter as rotas backend antigas de Estatísticas. O job de CI mais amplo pode recriar api/web/worker e está explicitamente fora deste fluxo; não foi usado. É necessário um plano de release compatível para a API e o frontend, com ordem/compatibilidade e impacto avaliados, antes de uma nova execução.
6. O release também exige árvore limpa e SHA completo já alcançável por `origin/main`. A branch local atual é `feature/improve-individual-selection-download-and-private-layout`; há 151 entradas locais pendentes preexistentes. `deploy-prod-web.sh`, seu teste shell e a documentação do runbook aparecem como não rastreados no Git atual, então não foram presumidos disponíveis no host ou na branch de produção. Não foram staged, commitados, stashed nem enviados para publicação dados locais desta ou de outras tarefas.
7. O inventário de produção usado para aprovação deve ser novo e ligado ao SHA/código de aprovação exatos, conforme `docs/DEPLOY-PROD-WEB.md`. Não foi criado inventário remoto: o checkout falha no pré-requisito local de árvore limpa, o PostgreSQL dedicado também não está disponível e não há aprovação de um plano de deploy que atualize os dois serviços. O documento cita, como referência histórica a confirmar somente depois de resolver esses bloqueios, host `/opt/markina-gallery`, projeto Compose `markina-gallery`, serviço Nginx Markina na porta local `127.0.0.1:8080`, domínio `https://markina.pickyourpic.com.br`, e arquivo de ambiente rotulado `docker/.env.homolog` (sem ler ou expor seus valores). Esse não é um inventário atual.
8. **Plano de impacto zero necessário para retomada:** decidir e documentar o fluxo que entrega API + frontend sem recriar `worker`, dados, Redis, nginx ou serviços de terceiros; produzir release em branch/PR somente com arquivos desta change, passar revisão/CI e obter SHA em `origin/main`; no host, capturar inventário read-only atualizado e conferir todos os manifestos/hashes; apresentar ao proprietário SHA, estado corrente, recursos/portas/domínio, ordem de atualização, controles de healthcheck, possível interrupção e rollback; somente então gerar e aprovar o código associado àquela execução e publicar. Ausência de migrations não elimina a necessidade de publicar o backend alterado.
9. Os testes de política do runbook atual passaram, mas verificam o script local em seus limites declarados e não habilitam release multi-serviço. Nenhuma conexão, comando Docker, fetch remoto ou mutação no host foi executada. O teste de cinco corridas exige o PostgreSQL dedicado, ausente em `127.0.0.1:55458`.

Revisão humana do resultado e dos artefatos precede sincronização/arquivamento OpenSpec. Publicação só pode ser retomada após o bloqueio multi-serviço, o estado Git limpo/revisado e o inventário atual específico serem resolvidos conforme o procedimento do projeto.

Nenhuma funcionalidade solicitada ficou parcialmente implementada. As pendências acima são validações/aceite em condições que não foram exercitadas nesta execução.

## Atualização de integração — 18/10/2026

A integração foi repetida em worktree isolado sobre a `main` atual e preserva os estados financeiros mais novos (`verifying`, `exception` e `hold`), metadados de pagamento com cartão e o fluxo condicionado de download de fotos compradas. A chamada de escopos agrupados foi atualizada para fornecer o tenant autenticado.

- Backend: 13 testes novos de pagamentos/status e 8 regressões existentes de dashboard, PIX, pedidos e reabertura passaram.
- Frontend: 26 testes passaram em 5 arquivos; lint dirigido, typecheck e build de produção passaram.
- Playwright/Edge com APIs sintéticas: 6 combinações (390/768/1440 px × claro/escuro), 18 capturas; filtros, CSV, histórico vazio, Estatísticas 404, miniaturas sob demanda, lightbox, teclado e foco passaram.
- Os resultados detalhados e limites estão em `openspec/changes/modernize-sales-payments-and-retire-statistics/validation.md` e `design-qa.md`. As capturas deste checkpoint foram geradas em `%TEMP%/sales-visual-qa-current` e não são rastreadas pelo Git.
- O PR de coordenação API/web #222 foi integrado em `main` após todos os checks obrigatórios passarem. Isso remove o bloqueio histórico de não haver fluxo coordenado para API e web; a publicação da feature ainda exige o PR desta change, inventário read-only atual no host e confirmação do impacto/rollback conforme as instruções do repositório. Nenhuma publicação de produção foi executada nesta atualização.
