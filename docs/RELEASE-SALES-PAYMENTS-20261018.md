# Release de Vendas e pagamentos — 18/10/2026

## Resultado confirmado

O [run 39135274157, tentativa 2](https://github.com/conradodeita/markina-gallery/actions/runs/39135274157/attempts/2) terminou com `success`. `production-app-preflight` e `production-app-release` passaram. O proprietário aprovou o environment protegido `production` e confirmou a aprovação nesta sessão.

- PRs integradas: #223 (dashboard) e #224 (allowlist operacional).
- SHA publicado: `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`.
- Checkout anterior: `ffea8c437b9940498487476f6167fdeec1067e2e`.
- Host: `clearbudget-vnic`, `132.145.193.169`; SSH 22; projeto `markina-gallery` em `/opt/markina-gallery`.
- Domínio: `https://markina.pickyourpic.com.br`; bind Nginx `127.0.0.1:8080`.
- Serviços construídos/recriados: somente `api` e `web`; Nginx Markina validado e recarregado.
- Schema antes/depois: `20261017_0084`; migrations: nenhuma.
- Fingerprint aprovado: `747eda3c382db1ef73bb76e042425d2dfdcc41649398504793543c8cca6255ed`.
- Release saudável registrado às `2026-10-18T15:11:38Z`.

## Wrapper e preflight

A inspeção SSH confirmou `root:root`, modo `0755`, arquivo regular e sintaxe válida. A única diferença para o wrapper revisado era o pin app antigo `37e9c17b4affe5e8a823a8be93e186b4e4ad226d`.

A cópia foi substituída atomicamente pela versão revisada, preservando a anterior em `/var/backups/markina-gallery-preflight-ssh-wrapper-20261018-fe1f3bc6`. A instalação foi verificada por conteúdo, sintaxe, owner/mode, blob Git `95f04139093a146c8f66ddd60e299ff76f57e2b3` e SHA-256 `253f9407a322822122d8339216ea9895482e386749b795c6724d524de4f8bfb2`.

O pin app passou a `6767d0ba092adb23666ab612db505af2e0900b35`; o pin facial foi preservado. A chave dedicada recusou o comando arbitrário `true`. O preflight que havia falhado foi repetido, aproveitando as suítes já aprovadas do mesmo SHA.

## Verificações posteriores

- SSH confirmou o checkout publicado e API/web saudáveis.
- Consultas somente-leitura confirmaram Alembic `20261017_0084 (head)` e `APP_VERSION=fe1f3bc6e1a483bd1ac5f4e71149f903e724873f` no container da API.
- `docker ps`, restrito à Markina, mostrou workers e Nginx com uptime de 15 horas e banco/Redis com uptime de três dias; somente API/web apresentaram reinício do release.
- HTTPS: `/healthz` e `/api/health` retornaram 200; `/admin/payments` retornou 200; `/admin/statistics` retornou 404.
- A pipeline verificou saúde, configuração efetiva, bind e smoke HTTPS antes de registrar sucesso.

O HTTP 200 administrativo confirma disponibilidade da rota, sem comprovar interação autenticada. A revisão visual e os fluxos foram validados anteriormente com dados sintéticos; esta verificação de produção não efetuou OTP, alteração de pedido ou ação financeira.

## Recuperação e continuidade

O fluxo preservou imagens anteriores e o SHA ativo. Eventual rollback usa `workflow_dispatch` com `app-rollback`, inventário novo e aprovação protegida antes de restaurar somente API/web. A cópia anterior do wrapper também foi preservada.

Após o release confirmado, o baseline versionado foi avançado para o SHA saudável publicado. Os hashes dos runtimes, schema e gates faciais não foram alterados na reconciliação documental.

Validação local do encerramento: política do workflow aprovada, 12 testes de classificação e 10 testes de escopo aprovados, Ruff e `git diff --check` aprovados. A mesma versão OpenSpec fixada no CI (`@fission-ai/openspec@1.14.0`) aprovou todos os 120 itens em modo estrito. A versão local sem pin, `1.14.1`, emite avisos estritos preexistentes sobre comprimento de requisitos; isso explica o resultado diferente da tentativa ampla anterior.

A revisão documental foi classificada contra o baseline publicado: `release_scope=none`, `app_release_ready=true`, critério `somente_api_web`. A reconciliação não seleciona outra publicação.
