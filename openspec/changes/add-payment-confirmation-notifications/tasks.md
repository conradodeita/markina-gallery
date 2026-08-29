## 1. Pagamento manual e persistência

- [x] 1.1 Criar migration aditiva para comunicação de pagamento, decisão imutável, templates controlados e caixa de saída, verificando upgrade e downgrade em banco sintético. (SQLite sintético aprovado em 2026-08-29)
- [x] 1.2 Implementar API autorizada para o cliente comunicar pagamento próprio e verificar testes de isolamento e idempotência. (`test_client_reports_own_pending_payment_idempotently`: aprovado em 2026-08-29)
- [x] 1.3 Implementar API administrativa para listar, confirmar ou recusar comunicações e verificar auditoria, estado financeiro e histórico do cliente. (testes de confirmação, recusa e listagem aprovados em 2026-08-29)

## 2. Notificações transacionais

- [x] 2.1 Implementar porta WhatsApp, worker de caixa de saída, limite de tentativas e configuração exclusiva por ambiente, verificando testes com adaptador sintético. (`test_messaging.py` e testes focados do worker: 10 aprovados; `ruff` focal e `docker compose ... config --quiet`: aprovados em 2026-08-29)
- [x] 2.2 Implementar templates de confirmação e recusa com variáveis controladas, verificando validação, renderização e ausência de dados sensíveis em logs. (`test_payment_templates.py` e renderização focal do worker aprovados; `ruff` focal aprovado em 2026-08-29)
- [x] 2.3 Enfileirar aviso ao fotógrafo e resposta ao cliente a partir das transições válidas, verificando que reexecuções não duplicam decisão ou mensagem. (3 testes focados de comunicação/decisão e 13 testes de mensageria/worker aprovados em 2026-08-29)

## 3. Interface, qualidade e operação

- [x] 3.1 Implementar telas de comunicação do cliente, revisão do fotógrafo e configuração de mensagens, verificando estados pendente, confirmado, recusado e entrega falha. (4 testes backend e 12 testes frontend aprovados; `tsc --noEmit` e ESLint focal sem erros em 2026-08-29)
- [x] 3.2 Cobrir autorização, idempotência, limites, tentativas, destino verificado e privacidade com testes automatizados. (5 testes de pagamento e 14 testes de mensageria/mídia aprovados; `ruff check app tests` aprovado em 2026-08-29)
- [x] 3.3 Validar lint, build, migrations, OpenSpec e homologação exclusivamente com dados sintéticos e adaptador sandbox. **Evidência:** a validação local aprovou migration `20260829_0014` em upgrade → downgrade → upgrade sobre SQLite sintético, 78 testes backend com Ruff, 42 testes frontend com typecheck/lint/build e OpenSpec estrito. O run GitHub Actions `33279596997`, para o SHA `751d746878aaad27885ba9297c88cf05ef5737f6` integrado em `develop`, aprovou backend, frontend, OpenSpec, gitleaks e deploy protegido em `homolog`; o log confirmou backup lógico, imagem de migration construída no SHA alvo, Alembic `20260829_0014 (head)`, worker/API/web saudáveis e registro da revisão. Os smokes externos `/healthz`, `/api/health` e `/admin/payments` responderam 200 em 2026-08-29. Nenhum provedor real ou dado real foi acionado; a configuração nova permaneceu no padrão sandbox.
- [x] 3.4 Atualizar documentação de segredos, ativação do provedor, templates e procedimento de rollback, verificando que nenhuma credencial é versionada. (`docs/OPERACAO-NOTIFICACOES-PAGAMENTO.md`, `.env.example`, Compose e ligação com a operação PIX revisados; busca por valores preenchidos e `git diff --check` aprovados em 2026-08-29)

## Registro de bloqueio — 2026-08-28

- A change está pronta para execução no OpenSpec, mas permanece bloqueada por dependência de produto explícita do roadmap: ainda não há change ativa nem contrato consolidado para preço por faixas, carrinho, checkout e PIX manual que crie o pedido pendente no qual a comunicação de pagamento incide. `SaleOrder` já possui estado pendente, porém não há fluxo especificado que o produza; iniciar a migration e as APIs desta change agora inventaria ou fixaria essa dependência fora do roadmap/OpenSpec. Nenhuma checkbox foi marcada. A retomada requer primeiro uma change aprovada que especifique e implemente preço, carrinho, checkout e PIX manual, com o contrato de pedido pendente.

## Resolução do bloqueio — 2026-08-29

- A dependência foi especificada e implementada pela change `add-manual-pix-checkout`; a confirmação/notificação foi integrada sobre esse contrato, validada no CI e publicada em homologação no SHA e run registrados na tarefa 3.3.
