# Evidência da preparação

## Implementação local

Foram implementados o coordenador fail-closed (`scripts/preview_worker_maintenance_flow.py`), o inventário somente leitura e sanitizado (`scripts/preview_worker_security_inventory.py`), o journal privado e atômico (`scripts/preview_worker_security_journal.py`), o adapter Linux para manutenção/rollback (`scripts/preview_worker_security_release_host.py`) e a CLI explícita (`scripts/preview_worker_security_release.py`). A CLI oferece `inventory`, `release` e `recover`; nenhum modo foi executado contra Oracle.

O adapter exige SHA, imagem e arquitetura ARM64, Compose reproduzível, serviços saudáveis, lock comum, fila drenada, ausência de produtores opcionais e fingerprint aprovado para janela e política de callbacks. O journal é persistido antes de cada mutação. A troca afeta somente `preview-adjustment-worker`, usa imagem por ID e `--no-deps --no-build --pull never`, com overlays diferentes para candidato e recuperação. As políticas de restart são conferidas e restauradas, inclusive o limite `on-failure:N`; divergências bloqueiam. Nenhum executor de migration, SSH, release web/API ou alteração de schema é chamado.

A revisão e os ensaios encontraram e corrigiram três problemas concretos:

- O Compose rejeita `build: null`; o overlay agora muda somente `image` e proíbe build/pull.
- RawTherapee 5.13 imprime o banner correto de `--version`, mas retorna código 2. O gate aceita somente os códigos 0/2 e ainda exige o banner exato; qualquer outra saída/código bloqueia.
- O reload do Nginx pode responder antes de a barreira entrar em vigor. O fluxo agora consulta até 15 segundos e só prossegue depois de observar HTTP 503. A verificação final preserva o hash original se o container do worker não tiver sido recriado e exige o hash do overlay após uma recriação.

Recibos idempotentes exigem conteúdo/permissões coincidentes; o journal rejeita diretórios POSIX acessíveis a grupo/outros. Os hashes do Nginx preservam bytes, inclusive whitespace, para restauração verificável.

## Validações executadas

- Suíte Windows: `python -m unittest scripts.test_preview_worker_maintenance_flow scripts.test_preview_worker_security_inventory scripts.test_preview_worker_security_journal scripts.test_preview_worker_security_release_host -v` — 47 testes aprovados; 2 skips esperados para `flock` e permissões POSIX indisponíveis no Windows.
- A mesma suíte em container Linux local, Python 3.13, sem rede, raiz read-only, usuário sem privilégios, capacidades removidas e scripts montados read-only — 47 testes aprovados, sem skips; exercitou o `flock` real e permissões POSIX.
- `python -m py_compile` nos módulos e testes — aprovado.
- `ruff check` e `ruff format --check` nos arquivos implementados — aprovados.
- `openspec validate release-preview-worker-security --strict` — aprovado.
- `git diff --check` — aprovado; os avisos de CRLF são dos artefatos locais preexistentes fora da change.
- PR #351 aberto e pronto para revisão humana; não mesclado. O PR inclui somente os commits/documentos da change e os 12 arquivos listados no escopo da implementação.
- Compose real: configuração de overlay com `image=sha256:...` aceita por `docker compose config --hash`; `build: null` reproduzido como inválido.
- Nginx 1.27 isolado: configuração temporária passou `nginx -t`.
- Rehearsal end-to-end em dois projetos Compose aleatórios, cada um removido pelo seu próprio manifesto: (a) baseline antigo substituído pela imagem candidata ARM64; (b) candidato baseline deliberadamente incompatível recusado e imagem anterior restaurada. Os dois fluxos confirmaram healthchecks, recibo/journal, três smoke tests HTTP 200 após conclusão e IDs inalterados dos demais serviços. A barreira foi observada como HTTP 503 antes das pausas. O segundo cenário terminou com recibo de recuperação.
- Rehearsals usaram somente imagens locais (`--pull never`, `--no-build`), bancos PostgreSQL descartáveis em `tmpfs`, Redis descartável, rede interna para API/worker/DB/Redis e porta Nginx vinculada a loopback. Não houve volume persistente, migration, dado/segredo real ou tráfego de aplicação. O teardown foi `docker compose -p <projeto-aleatório> -f <manifesto-temporário> down --remove-orphans`; nenhum prune ou remoção de imagem foi executado.

## Ambiente e limites

O daemon é compartilhado (Engine ID `91f58054-ec8c-45fa-8aa5-93882807fbcf`), x86_64/WSL2, e Compose local 5.6.1; a imagem ARM64 foi executada por emulação, não em host ARM nativo. Para o host Windows, o harness adaptou `/dev/null` para o dispositivo local e substituiu somente o lock `flock` por contexto vazio; os testes Linux separados exercitam o lock real. A rede de ingresso sintética foi uma bridge dedicada para permitir a sonda loopback do host; somente Nginx se conectou a ela, sem chamadas externas configuradas. Portanto, o rehearsal prova o fluxo no daemon local, mas não equivale à execução no host Linux de produção nem valida a versão de Compose 2.35.1 do servidor.

Antes/depois dos ensaios, os IDs dos containers dos projetos existentes `markina-gallery` e `firefly_telegram` permaneceram iguais. `firefly_bot` já aparecia em `Restarting (1)` antes dos ensaios; não foi tocado e não há evidência para atribuir ou excluir causalidade. Todos os projetos e redes temporários do rehearsal foram removidos; as imagens locais foram preservadas.

## Evidência reutilizada

A imagem ARM64 candidata `sha256:ef5105e0bcd734b929d2b46945f7538dceccade45a60d806bd58a2b3b4bff45d` e os pins Python permanecem cobertos também por `openspec/changes/prepare-coordinated-python-security-release/preview-worker-preparation-20261030.md`. O rehearsal confirmou a validação de versões, `pip check` e RawTherapee na transição real do adapter; JPEG/PNG e contratos HTTP foram validados anteriormente e não foram repetidos.

## Gates externos

A implementação continua opt-in e não resolve retroativamente o bootstrap de processos legados. A análise somente do código versionado encontrou o endpoint `POST /api/mercadopago/webhooks/{account_id}` para eventos `type=order`: valida assinatura, persiste a identidade idempotente em `MercadoPagoWebhook`, faz commit antes de retornar `received`, e o worker consome a inbox. O worker também reconcilia pagamentos enviados via consulta ao provedor; há testes sintéticos para pagamento aprovado e reembolso detectados sem callback (`backend/app/mercadopago_api.py`, `backend/app/mercadopago_webhook.py`, `backend/app/worker.py`, `backend/tests/test_mercadopago_webhook.py`). A spec/teste de aposentadoria confirma que a rota legada InfinitePay não faz parte das rotas atuais (`openspec/specs/gallery-sales/infinitepay-retirement/spec.md`, `backend/tests/test_checkout_retirement.py`).

Em 31/10/2026, a documentação oficial do Mercado Pago para [notificações Checkout Pro com Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/notifications?scope=prod) exige confirmação HTTP 200/201 e informa novas tentativas quando a confirmação não chega, com intervalos progressivos. A mesma documentação lista tópicos opcionais e informa que alertas `stop_delivery_op_wh` não seguem a retry policy usual ([notificações opcionais](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/optional-notifications?scope=prod)). Como o fluxo de manutenção espera HTTP 503 durante a barreira, concluir que esse status provocará retry é uma inferência de que 503 não é confirmação 200/201; a página não especifica uma tabela de retry por código HTTP. A documentação sustenta retry para Orders, mas não prova a configuração efetiva das contas Pick-your-Pic.

Permanecem não verificados: URLs e tópicos ativos em cada conta, eventual inscrição em tópicos opcionais não suportados pelo endpoint, e a aceitação explícita do proprietário para a janela e o risco residual. Nenhuma credencial, dado operacional ou ambiente Oracle foi consultado. Esses gates impedem execução na Oracle; nenhuma execução remota foi feita ou autorizada nesta change.
