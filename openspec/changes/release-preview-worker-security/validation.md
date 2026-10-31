# Evidência da preparação

## Continuação de preparação em 31/10/2026

PR #351 foi integrado por solicitação explícita do proprietário: main `6af538ecd5c46da7691fa973c33869f263945a25`, CI pós-merge `41194332664` aprovado, classificação protected, publicação ignorada. O proprietário declarou Mercado Pago Orders habilitado, nenhum tópico opcional e aceitou indisponibilidade temporária de callbacks. Isto não comprova configuração externa das contas. Data/horário da janela ainda não foram fornecidos; nenhuma execução de release foi autorizada por esta preparação.

Inventário remoto somente leitura em 31/10 às 08:24 BRT: checkout limpo `0dd015a62447e0c8d4c6af16b381140c8118f2ec`, schema `20261026_0090`, fila preview_adjustment com zero queued, processing e failed; nenhum marcador de tentativa pendente. API/worker principal executam aiohttp 3.14.4, multidict 6.9.1, urllib3 2.8.0 e yarl 1.25.1. Prévias ainda executa 3.14.3/6.8.0/2.7.0/1.24.5. Os opcionais faciais/Gemma/RAW parados são condição prevista, não evidência de incidente novo. Checkout antigo preservado também é deliberado: a correção preserva código e camadas, não publica toda a main.

Preparação local adicional: seleção explícita de Compose 5.6.1, profiles em consultas por serviço, preservação de identidades históricas paradas sem recriação e suporte a operador root com lock do mesmo dono do diretório privado. Serviços ativos e produtores pausados continuam exigindo proveniência completa. Nenhuma permissão/ACL foi alterada na Oracle. Testes: 55 executados no Windows (3 skips POSIX); 55 aprovados em Linux ARM64 emulado sem skips, usuário sem privilégios, sem rede e filesystem read-only. Ruff e OpenSpec strict aprovados. Ensaio Linux separado de root em diretório descartável pertencente a UID 1001 confirmou flock/journal reais e preservação dos donos. Esse ensaio precisou de CHOWN, DAC_OVERRIDE e FOWNER dentro do container descartável; a primeira tentativa com apenas CHOWN foi recusada por permissões, sem efeito na Oracle. Revisão local do diff não identificou refatoração adicional necessária; nenhum código funcional da aplicação foi alterado.

Artefato local `C:\codex-data\release-evidence\preview-python-20261031\candidate-arm64.tar`: 1.087.364.608 bytes, SHA256 `2ce49fe41611252d7cf4721fc79ac92d0c4c6ff740635d67ae729ac73cec81e2`. Exportado de candidato local `sha256:ef5105e0bcd734b929d2b46945f7538dceccade45a60d806bd58a2b3b4bff45d`; o config transportado tem SHA256 `e88e70fd78698a9fc6a327cf990296b01e72fd408b0ed9e048760dee125e31bf`, linux/arm64. NÃO presumir que ID containerd e ID após importação no daemon Oracle sejam intercambiáveis; comprovar config/camadas e o ID real antes do inventário. Nenhuma importação Oracle ocorreu. Rollback atual confirmado por ID `sha256:48fa9dc8a2c94d5398a502ad02fcbcab89a660039c66d08470c0ae82e81ce44e`, linux/arm64.

### Bloqueios operacionais comprovados

- Imagem candidata ainda ausente do daemon Oracle. O inventário oficial completo não foi executado e nenhum fingerprint operacional foi emitido.
- Diagnóstico privilegiado exclusivamente read-only reproduziu hashes Compose de API, worker principal, web, Redis, evolution-redis e worker de prévias. Não reproduziu Nginx, db, evolution-api e evolution-db. Nos três últimos há diferenças de ambiente (respectivamente 3, 2 e 1 chaves entre manifestos atuais e containers). Somente contagens/comparações foram retornadas, sem valores. Para Nginx a causa do hash divergente ainda não foi determinada; as verificações parciais de imagem, ambiente, comando e entrypoint não explicaram a divergência. Não atribuir todos os hashes à mudança de versão do Compose: vários hashes coincidem entre 2.35.1 e 5.6.1.
- Esses gates permanecem bloqueantes. Reconciliar a proveniência/configuração aprovada antes de publicar; não regravar labels, alterar credenciais, recriar serviços vizinhos ou reconstruir snapshots para forçar aprovação. A correção de segurança de prévias não autoriza alterar configurações dos bancos/Evolution.
- Falta definir a janela e confirmar o fingerprint gerado com candidato importado e configuração reconciliada. O diagnóstico read-only não equivale a inventário sob lock nem a autorização de mutação.

Evidências locais sanitizadas: `oracle-readonly.json`, `compose-readonly-diagnostic.json`, `candidate-transport.json` e `executor-provenance.json` no diretório de artefatos acima. Os scripts de diagnóstico capturaram somente metadados, hashes e consultas SQL em transação READ ONLY com timeout; nenhum dado de cliente, fotografia ou valor secreto foi retornado. A fonte operacional e containers permaneceram preservados; não houve fetch remoto, build na Oracle, alteração de imagem, pausa, migration ou publicação.

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
