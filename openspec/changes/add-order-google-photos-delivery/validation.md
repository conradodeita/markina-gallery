## Estado em 2026-09-25

Implementação autorizada pelo proprietário com “Aplique a change”. Branch feature/order-google-photos-delivery criada em origin/develop f60f828, preservando todo trabalho local preexistente. Nenhuma mensagem real, alteração remota ou deploy executado.

Pedido original: trocar histórico visual de mensagens no card administrativo por link Google Photos por pedido; preservar prévias em Compras e mostrar botão verde disponível/cinza indisponível. Complemento durante planejamento: botão Enviar também gera notificação configurável na central existente. Artefatos reconciliados para esse complemento, retirando a hipótese inicial de disponibilização silenciosa. Remoção de link continua silenciosa.

Não criar backup/arquivo paralelo do histórico visual retirado. Não apagar filas transacionais compartilhadas ou histórico financeiro: permanecem necessários para as notificações existentes e a nova notificação pedida. Nenhuma tabela de comunicação será expurgada por esta change.

## Continuidade

Branch local encontrada: `feature/client-gallery-covers-payment-review`; PR #97 já integrado conforme registro da change anterior. Preservar todos os arquivos previamente modificados, inclusive registros de outras changes, `backend/app/facial/purge.py` e `.codex-tmp/`. Não incluir esses arquivos no commit futuro.

Proposta e refinamentos aceitos; implementação autorizada. Completar tarefas com evidências e seguir push + PR → parada para CI humano. Não presumir que aprovação da proposta autoriza deploy ou mensagens reais de teste.

## Validação de planejamento

`openspec status --change add-order-google-photos-delivery`: quatro artefatos obrigatórios completos (proposal, specs, design, tasks). `openspec validate add-order-google-photos-delivery --strict --no-interactive`: válido. Testes do produto não executados nesta etapa porque somente arquivos de planejamento foram criados.

## Evidências de implementação

- Mandato/roadmap reconciliados com as decisões aprovadas.
- Migração aditiva 0061 e validador de URL: 20 testes passaram em 23,82 s, incluindo upgrade de pedido existente em SQLite. PostgreSQL ainda não executado.
- Matriz de notificações: sete eventos, com regressões de configuração aprovadas (8 testes).
- Testes iniciais de API revelaram dados incompletos na fixture (ajustados) e ausência da chamada de validação de origem nos novos endpoints (corrigida). Nova execução aprovada, conforme evidências abaixo.

- API/configuração/worker: 26 testes passaram em 12,90 s. Cobertura adicional de entrega: 14 passaram em 11,28 s, incluindo PIX agrupado, correção/reconfirmação, revogação de avisos, TTL, push independente e destino privado.
- Frontend: 32 testes passaram (formulário, pagamentos, Notificações, compras e biblioteca), em 50,31 s.
- Ruff completo passou. OpenSpec estrito completo: 60 itens passaram.
- PostgreSQL local indisponível: porta dedicada 55458 sem serviço, daemon Docker Desktop não está em execução. Nenhum serviço de terceiros iniciado/alterado. Testes locais de migração/transação usam SQLite; locks PostgreSQL seguem a ordem cliente → pedido já usada pelo fluxo financeiro, sem validação concorrente PostgreSQL nesta etapa.

## Checkpoint final local

- Build de produção (`npm --prefix frontend run build`) passou com checagem TypeScript e geração das 22 páginas, inclusive após o ajuste final de estilo do campo de entrega.
- ESLint completo: zero erros, 28 avisos preexistentes. Ruff completo: aprovado novamente em 25/09. OpenSpec via `npx --yes @fission-ai/openspec@latest validate --strict --all --no-interactive`: 60 itens aprovados; avisos informativos de arquivo de outras changes permanecem fora do escopo.
- Segunda rodada frontend: `npm --prefix frontend test -- app/admin/payments/order-delivery.test.tsx app/library/order-delivery.test.tsx app/library/library.test.tsx app/admin/payments/payment-actions.test.tsx app/admin/galleries/orders.test.tsx`: 32 testes passaram, incluindo proteção contra duplo clique e regressões financeiras.
- Navegador Chromium sobre o build local, APIs interceptadas com dados sintéticos e rede externa bloqueada: 320, 390 e 1440 px, temas claro/escuro, seis combinações aprovadas. Conferidos digitação sem envio, Enviar, Reenviar, link verde com destino/atributos seguros, botão indisponível, prévia protegida/ampliação/Escape, foco, configuração dos dois canais e ausência de overflow. Campo ajustado para altura mínima de 44 px e fonte de 16 px; cenários repetidos após rebuild. Capturas e relatório apenas locais em `.codex-tmp/order-delivery-ui/`, sem dados pessoais e fora do Git.
- Dois testes de concorrência em `test_order_delivery_concurrency.py` preparados para PostgreSQL dedicado: localmente ignorados com motivo explícito. Não representam validação real de locks PostgreSQL; nenhuma infraestrutura compartilhada foi modificada.
- A suíte ampliada anterior perdeu a saída final na interrupção da sessão. Sua execução foi reiniciada; a primeira tentativa usou por engano o Python global sem `py_vapid` e falhou na coleta. A retomada usa `backend/.venv/Scripts/python.exe`, com as dependências existentes do projeto.
- Regressão ampliada concluída: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_order_delivery.py backend/tests/test_order_delivery_url.py backend/tests/test_notification_settings.py backend/tests/test_notification_delivery.py backend/tests/test_unified_checkout.py backend/tests/test_derived_galleries.py -q --tb=short --basetemp .codex-tmp/order-delivery-integration4`: **145 passaram, 3 ignorados**, em 406,43 s. Ignorados são cenários de concorrência PostgreSQL da suíte existente. Inclui projeções em lote, correções financeiras, galerias, propriedade e histórico de compras. Log local fora do Git: `.codex-tmp/order-delivery-integration4.log`.
- Verificação final: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_order_delivery.py backend/tests/test_order_delivery_migration.py backend/tests/test_order_delivery_concurrency.py backend/tests/test_notification_payments.py backend/tests/test_payment_shortcut_projection.py -q --tb=short --basetemp .codex-tmp/order-delivery-final1`: **19 passaram, 2 ignorados**, em 25,01 s. Inclui nova asserção da projeção administrativa, upgrade preservando pedido e regressões de notificações/atalhos. Os dois ignorados são os novos cenários PostgreSQL já descritos.

## Entrega para revisão

Diff revisado e `git diff --cached --check` aprovado. Somente os 31 arquivos da entrega estão preparados para commit; alterações preexistentes em outras changes, `backend/app/facial/purge.py` e temporários continuam fora dele. Publicar `feature/order-google-photos-delivery` em PR para `develop` e parar aguardando o proprietário confirmar CI verde. Não consultar repetidamente o CI, integrar, publicar em homologação nem arquivar/sincronizar a change nesta etapa. A task 4.3 será encerrada no registro local após confirmação de push/PR.

Push confirmado em 25/09/2026: commit 398a18f, branch feature/order-google-photos-delivery. PR #98 aberto para develop: https://github.com/conradodeita/markina-gallery/pull/98 e anexado à tarefa. Execução parada após push + PR, aguardando confirmação humana do CI. Este fechamento de continuidade é local, posterior ao commit publicado; nenhum CI foi consultado, merge ou deploy executado.

## Correção do CI — PR #98

Após o proprietário informar falha, consultado o run 36161547426 do commit 398a18f. Frontend e OpenSpec passaram. Backend teve 814 aprovados, 13 ignorados e uma falha: o teste de histórico após remoção da galeria comparava o JSON inteiro sem incluir o novo campo `delivery_album_url`. A expectativa agora inclui `None` para pedidos antigos sem álbum, preservando todas as demais verificações de mídia e isolamento.

Gitleaks 8.24.3 sinalizou somente a chave sintética `delivery-correction-1`, usada como identificador de idempotência no teste. Acrescentada expressão ancorada para esse valor exato à lista existente de fixtures sintéticas em `.gitleaks.toml`. Nenhuma regra foi desativada nem diretório ignorado. Apenas renomear o valor não resolveria a varredura do histórico; não houve reescrita de commits ou force push.

Validação da correção: 15 testes passaram em 14,55 s (cenário que falhou e módulo `test_order_delivery.py`) usando o Python do projeto e banco SQLite temporário isolado. Ruff completo aprovado e diff sem erros de whitespace. Executável oficial gitleaks 8.24.3, baixado para temporários locais e conferido pelo SHA-256 publicado: varredura Git de 300 commits, 11,26 MB, sem vazamentos. Artefatos/logs permanecem em `.codex-tmp/`, fora do commit. Não houve alteração no código de produção, frontend ou migration.

Preparar novo commit apenas com teste, exceção exata e continuidade desta change. Fazer push no mesmo PR e parar novamente para o proprietário confirmar CI, sem merge/deploy.
