## 1. Contratos e persistência

- [x] 1.1 Confirmar o aceite dos artefatos e registrar a reconciliação da tabela de supersessão do design nos documentos de continuidade afetados, sem arquivar ou sincronizar specs prematuramente; verificar que nenhuma tarefa ativa manda reintroduzir finalização obrigatória por galeria. Evidência: aceite explícito “ótimo! implemente”; continuidade das duas changes anteriores reconciliada e tarefas consultadas, sem sincronizar specs principais.
- [x] 1.2 Criar modelo e migration aditiva para agrupamento, revisão, snapshots, vínculos e comunicação única; validar upgrade em banco isolado com pedidos legados, constraints de pertencimento/idempotência e preservação integral dos registros existentes.
- [x] 1.3 Implementar projeção autenticada do carrinho global com agrupamento visual, pastas, contagem e preços por escopo vigente; testar uma/múltiplas galerias, múltiplas pastas, referências repetidas, isolamento de clientes e impedimentos sem total parcial pagável.

## 2. Revisão e pagamento

- [x] 2.1 Implementar preparação idempotente da revisão e snapshot PIX do grupo, reutilizando rascunho válido; testar repetição, mudanças de seleção/cotação, ausência de configuração, código com valor fixo incompatível e manutenção do PIX iniciado após alteração global.
- [x] 2.2 Adaptar sincronização de seleções/rascunhos e locks para a revisão agrupada, incluindo remoção de item expirado sem liberar novas inclusões; testar que alterações invalidam a revisão anterior e não modificam pedidos congelados.
- [x] 2.3 Implementar comunicação única com validação de revisão e transação integral; testar congelamento e consumo exato das seleções, rollback por falha intermediária, tentativa de acesso alheio e repetição após expiração posterior ao primeiro sucesso.
- [x] 2.4 Proteger rotas legadas e recuperar checkouts já iniciados sem reescrever snapshots; testar agrupamento com PIX compatível, conflito explícito entre snapshots divergentes e preservação das ações de pedidos antigos sem grupo.
- [x] 2.5 Executar testes de concorrência em PostgreSQL para duas preparações, comunicações simultâneas, alteração de seleção concorrente e decisões concorrentes; comprovar ausência de duplicidade, atualização parcial e interbloqueio por ordem de locks.

## 3. Operação administrativa e histórico

- [x] 3.1 Implementar serviço conjunto de confirmação, recusa e correção e adaptar atalhos administrativos; testar alcance explícito do conjunto, atomicidade de todos os integrantes, auditoria, idempotência e comportamento legado.
- [x] 3.2 Estender eventos/outbox de pagamento para o grupo e seus destinos autorizados; testar um evento lógico por transição/canal habilitado, correção silenciosa, repetição sem duplicação e falha de transporte sem desfazer a transação financeira.
- [x] 3.3 Implementar projeção e detalhes de compras agrupadas coexistindo com pedidos legados; testar pagamento informado, confirmado e recusado, fotos protegidas, expiração de seleção, entregas distintas e exclusão de rascunhos do histórico.
- [x] 3.4 Adaptar ficha individual para distinguir subtotal do pedido e total do PIX e revisar consumidores financeiros; testar exportação por pedido, operação de produção/entrega preservada e ausência de receita duplicada nos resumos existentes.

## 4. Experiência da cliente

- [x] 4.1 Implementar navegação compartilhada `Galerias`, `Carrinho (N)` e `Compras` nas telas autenticadas, inclusive convite e busca; testar acesso aos destinos, contador global atualizado, troca de conta e ausência de dados privados de sessão anterior.
- [x] 4.2 Transformar biblioteca na listagem de galerias sem cards duplicados e criar revisão direta em `/library/cart`; testar nomes, fotos por galeria/pasta, subtotais, total geral, um PIX/QR/Informar pagamento, carrinho vazio e erros por grupo.
- [x] 4.3 Conectar edição/retomada do carrinho e preparação da revisão com estados de gravação, conflito e tentativa novamente; testar sair e voltar, atualizar página, falha de gravação visível e revisão alterada em outra aba sem comunicação automática de conteúdo novo.
- [x] 4.4 Criar destino `/library/purchases` e detalhes agrupados com retorno aos outros destinos; testar compras informadas/confirmadas/recusadas, histórico legado, nova seleção independente e falha do histórico sem bloquear galerias/carrinho.
- [x] 4.5 Adaptar links flutuantes, URLs antigas, notificações e entradas `?mode=review`; testar navegação direta para revisão global e manutenção do destino correto de pedidos históricos ou checkouts legados incompatíveis.
- [ ] 4.6 Validar interface em desktop e mobile estreito, teclado e leitor de tela; registrar evidência de foco, rótulos, safe areas, diálogos, ausência de sobreposição de botões e navegação nos três destinos sem perder seleção.

## 5. Integração e entrega

- [x] 5.1 Criar cenário de integração com duas galerias, duas pastas em uma delas, uma compra histórica e uma segunda identidade; comprovar seleção → revisão única → comunicação → decisão administrativa → histórico, retomada após novo login e isolamento entre clientes.
- [x] 5.2 Executar testes relevantes backend/frontend, lint, typecheck, build e validação OpenSpec; registrar comandos/resultados e revisar diff, migrations e ausência de segredos/arquivos não relacionados antes de declarar pronto para commit.
- [x] 5.3 Preparar roteiro de homologação com estados normais e exceções legadas, inventário/impacto restrito e estratégia de rollback compatível; verificar que o artefato inclui versões, serviços, portas/subdomínio e gates de autorização sem executar deploy não autorizado.
- [ ] 5.4 Após autorização aplicável, entregar por PR e homologação seguindo os controles do repositório; registrar evidência do CI e paridade do commit/serviços. Quando só restar CI, parar e aguardar o usuário informar o resultado, sem polling.
- [ ] 5.5 Registrar aceite humano do fluxo real em mobile/navegador e sincronizar/arquivar somente após essa revisão; verificar que specs consolidadas deixam de exigir PIX separado por galeria e preservam histórico, snapshots e proteções de acesso.

## 6. Estado e evidências

Implementação local em andamento em 20/09/2026, branch `codex/unified-client-cart-and-pix`. Nenhum deploy ou migration no banco real desta change. Itens marcados abaixo representam somente evidência já obtida; os gates humanos seguem pendentes.

Evidência do planejamento: `openspec validate unified-client-cart-and-pix --strict` retornou `Change 'unified-client-cart-and-pix' is valid`; `openspec status --change unified-client-cart-and-pix` informou os quatro tipos de artefato completos (proposal, specs, design, tasks). Foram criados quatro deltas de spec. Alterações locais anteriores e specs principais foram preservadas.

Evidência 1.2: `python -m pytest tests/test_unified_pix_migration.py -q` → 1 passou; upgrade sobre 0057 com pedido confirmado preservado, constraints de identidade e rascunho duplicado, downgrade vazio e recusa de downgrade com agrupamento existente. Backend funcional inicial: `.venv/Scripts/python.exe -m pytest tests/test_unified_checkout.py -q --tb=short` → 4 passaram (projeção, preparo/reenvio, revisão obsoleta/identidade e snapshot PIX). Demais cenários das tarefas seguem pendentes.


Validação de integração: `DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55458/markina_unified_test .venv/Scripts/python.exe -m pytest tests/test_unified_checkout.py -q --tb=short` → **14 passaram** (log local ignorado `unified-pg-v4.log`). Inclui duas galerias/três fotos/duas pastas, preços, identidade alheia, preparo/reenvio, alteração concorrente, decisões concorrentes, rollback, expiração/remoção, incompatibilidade de PIX legado e recuperação preservando recebedor, novo login, compra antiga e nova seleção independente. Cada teste PostgreSQL usa schema descartável próprio. Migration ensaiada também no PostgreSQL: **1 passou**, além do ensaio SQLite já registrado.

Frontend: suíte completa inicial **316 passaram / 1 falhou** por expectativa assíncrona antiga; corrigida e suíte focada `app/gallery/gallery.test.tsx app/admin/payments/payment-actions.test.tsx app/library` → **47 passaram** (`unified-final-focused.log`). As demais 43 suítes passaram na execução ampla. Nova verificação segue após ajustes finais de foco e acesso negado. `next build` concluiu (incluindo TypeScript); Ruff passou; ESLint teve zero erros e avisos de imagens/ref preexistentes e novos, a revisar no checkpoint final.

Visual automatizado sobre build de produção, APIs/imagens sintéticas, Chromium: **360/390/1440 px**, um PIX, duas galerias sem cards duplicados, navegação aos três destinos preservando seleção, comunicação e histórico agrupado, sem overflow nem sobreposição do botão financeiro pela barra. Capturas inspecionadas em `.codex-tmp/unified-ui/` (não versionadas). Roteiro, inventário, versões e rollback em `homologacao.md`; inspeção remota desta change não realizada. Tarefa 4.6 permanece parcial até completar verificação de teclado/foco e obter teste com leitor de tela real; 5.4/5.5 dependem de CI/autorizações/aceite aplicáveis.


Checkpoint final local: regressão backend ampla `tests/test_derived_galleries.py tests/test_global_pix.py tests/test_notification_payments.py tests/test_payment_shortcut_projection.py tests/test_gallery_lifecycle.py` → **154 passaram / 2 falharam** exclusivamente por igualdade estrita do JSON legado (novo `payment_groups` / `payment_group_id`). Expectativas atualizadas; reexecuções dirigidas comprovaram **2 passaram** (comunicação/entrada no histórico) e **1 passou** (mídia histórica isolada). O ensaio SQLite do checkout/migration resultou em **12 passaram, 3 skips** (os três cenários concorrentes são exclusivos de PostgreSQL e passaram nele). Não repetir a suíte de 15 minutos após mudanças apenas nessas expectativas.

Tarefas 3.2/3.4: `test_admin_scope_history_decisions_and_correction` passou após acrescentar falha sintética do transporte, deduplicação de eventos, correção silenciosa, subtotal da ficha, total do dashboard sem duplicação e escopo completo em filtro de uma galeria (`unified-admin-consumers.log`). Snapshot legado foi novamente validado com diferenças de instruções e preservação integral dos metadados (`unified-legacy-snapshots.log`: 1 passou).

Frontend final: `app/library app/admin/payments/payment-actions.test.tsx` → **25 passaram**, cobrindo foco, Tab/Shift+Tab/Escape, devolução ao acionador e remoção de fotos/PIX após 403. Build final de produção passou, incluindo TypeScript. Ruff passou; ESLint final **0 erros, 27 avisos** (uso de img e avisos não bloqueantes). `openspec validate --all --strict` → **55 itens válidos, 0 falhas**. Diff revisado; nenhuma alteração de `.env`, secret, migration destrutiva ou dado real incluída.

Pendências humanas: 4.6 apenas para leitor de tela real e aceite mobile autenticado (automação de semântica/foco/layout concluída); 5.4 aguardará CI/autorizações e execução de homologação; 5.5 depende da revisão do proprietário. Não sincronizar specs principais nem arquivar antes desse aceite. Capturas/DBs/logs locais de teste e documentos preexistentes de outras changes ficam fora do commit.

Fechamento de remoção: `test_empty_cart_discards_only_unreported_group` e proteção dos endpoints legados com prazo expirado passaram em PostgreSQL (**2 passaram**, `unified-empty-cart.log`). A remoção de todo o carrinho descarta apenas rascunhos e grupo não comunicado; pagamentos antigos continuam protegidos. Última alteração de código backend validada por esses testes; a formatação Ruff dos arquivos novos não altera comportamento.

Entrega preparada: 43 arquivos relacionados selecionados explicitamente, `git diff --cached --check` sem erro. Documentos preexistentes de outras changes, `.codex-tmp`, DBs, imagens e logs ficaram fora do staging. Publicar PR para `develop`, sem merge/deploy automático nesta change; parar quando apenas CI estiver pendente. Revisão humana e publicação/aceite remoto continuam pendentes nas tarefas 4.6, 5.4 e 5.5.

## Correção do CI do PR #90

O proprietário informou falha no backend. Run `35549331694`, SHA `72d21fecb829b83f4280101b9abeaece3f491ae9`: frontend/OpenSpec/gitleaks aprovados; backend teve **668 passaram, 10 skips e 1 falha** em `test_notification_upgrade_preserves_history_and_baselines`. A preparação do banco na revisão 0055 usava modelos ORM atuais, cujo INSERT passou a exigir `payment_group_id`, coluna criada somente na 0058.

Correção limitada à fixture histórica: INSERTs explícitos pelo contrato 0055 para pedido/comunicação/outbox, sem depender de modelos atuais. Preservados upgrade repetido, baselines, concorrência, privacidade e proteção contra downgrade; acrescentada verificação de identidade/status da comunicação e ausência de agrupamento retroativo após upgrade. Não alterado código de produção ou migrations. Validação dirigida em execução; publicar a correção somente após aprovação local e depois aguardar novo resultado do CI sem polling.

Validação da correção: `.venv/Scripts/python.exe -m pytest tests/test_transactional_notification_migration.py tests/test_unified_pix_migration.py -q --tb=short` → **2 passaram** em 76,76 s, somente avisos de depreciação SQLite; `ruff check backend/app backend/tests` passou. A falha do CI foi resolvida no teste dirigido; resultado da nova execução remota ainda será informado pelo proprietário.
