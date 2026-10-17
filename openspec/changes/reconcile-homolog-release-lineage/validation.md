# Validação

## Inventário somente leitura

- `39036156815`, esperado `71be3b29659143293351968e15fb4886c2d72bf0`: a guarda revelou `0779b3e4400f8511980c2d18e79ef8eea586a341` e encerrou antes de consultas.
- `39036197944`, esperado `0779b3e4400f8511980c2d18e79ef8eea586a341`: inventário concluído. Projeto Compose `markina-gallery`, entrada `127.0.0.1:8080`, domínio `markina.pickyourpic.com.br`, serviços ativos saudáveis, HTTP 200 em `/healthz` e `/api/health`, filesystem do projeto 64% usado e Alembic `20261016_0082`.
- Inventário apontou um container de migration antigo parado e workers órfãos de módulos opcionais. Nenhum container foi removido ou reiniciado.

## Bloqueio inicial e correção da proteção

- CI pós-merge #204 `39032173810`: backend, frontend, Gemma, OpenSpec, Gitleaks e inventário passaram; `deploy-homolog` foi rejeitado antes de executar passos porque `develop` não estava protegida.
- O ambiente `homolog` mantém `required_reviewers` e `protected_branches=true`. A branch `develop` agora exige os mesmos checks que `main` (`backend`, `frontend`, `gemma-runtime`, `openspec`, `homolog-inventory-policy`, `gitleaks`), bloqueia force-push e deleção e aplica as regras também a administradores. A regra de produção não foi alterada.

## Reconciliação local — registro histórico

- `main` tem 43 commits posteriores a `71be3b2`, incluindo a migration facial `20261016_0082`; `develop` e a migration de pastas da change #204 usavam outro arquivo com o mesmo identificador.
- Integração simulada apresentou apenas conflito em `.gitleaksignore`; a resolução preserva os fingerprints exatos e comentários de ambos os lados.
- A migration de pastas foi renomeada para `20261017_0083_private_upload_batch_folder_scope.py`, com `down_revision = "20261016_0082"`; o teste passa a atualizar a base `0081` até `0083`.
- `python -m alembic heads`: `20261017_0083 (head)`.
- `python -m pytest tests/test_private_upload_batch_migration.py -q`: 1 teste ignorado localmente porque o PostgreSQL sintético não está configurado; a regressão será executada no CI do PR.
- `openspec validate reconcile-homolog-release-lineage --strict`, `openspec validate fix-private-photo-notifications-and-admin-metrics --strict` e `openspec validate reveal-homolog-sha-on-inventory-mismatch --strict`: válidos.
- `git diff --check`: sem erros.
- CI `39036724855`: backend, frontend, Gemma e OpenSpec passaram; `homolog-inventory-policy` e Gitleaks falharam. Gitleaks apontou quatro fingerprints históricos conhecidos porque o conflito de `.gitleaksignore` havia concatenado linhas. As linhas foram restauradas; Gitleaks 8.24.3 local varreu 638 commits e não encontrou achados.
- O teste de política de produção falhou porque a PR de homolog altera `auth.py` e `main.py`, blobs fixados pelo gate facial, embora as mudanças sejam somente de upload/métricas. O step desse gate agora roda em PRs/pushes de `main`; o teste de política de homologação verifica a condição, e o gate facial continua obrigatório em `main`. Testes locais `scripts/test_deploy_homolog_policy.py` e `scripts/test_deploy_homolog.sh` passaram.
- Naquele ponto estavam pendentes: revisão do diff integrado, regressão PostgreSQL, CI integral no PR para `develop`, merge e deploy autorizado pelo gate do ambiente. As evidências posteriores abaixo substituem esse estado.

## Sem alteração remota de aplicação

Até a integração, o commit e o PR desta change, as atividades feitas no servidor foram somente os inventários aprovados. O job de deploy anterior falhou antes de iniciar; não houve backup, migration, build, restart ou alteração de dados.

## Integração e publicação concluídas — 17/10/2026

- PR #210 integrada em `develop` no commit `c9eaf6381cb95f53a1c88206f7b9d4fb638f7ef9`, com backend, frontend, Gemma, OpenSpec, política de homologação e Gitleaks aprovados. A correção posterior da leitura da revisão Alembic foi integrada pela PR #212 em `25cd338f7243a114e8151e6bda3d03204b12ae43`; sua causa e validação pertencem a `fix-homolog-deploy-stale-revision-probe`.
- [CI/deploy 39046656588](https://github.com/conradodeita/markina-gallery/actions/runs/39046656588), alvo `25cd338`: os seis checks requeridos e `deploy-homolog` concluíram com sucesso. Backend: lint aprovado; regressão facial de migration `1 passed`; referências/confirmação `34 passed`; suíte completa `1650 passed, 23 skipped`; concorrência multi-tenant PostgreSQL `4 passed`; checkout concorrente `1 passed`; inventário de exclusão `1 passed`.
- O job backend define as duas URLs de PostgreSQL sintético utilizadas pela fixture de `test_private_upload_batch_migration.py`. A regressão de escopo privado atravessa as revisões 0081, 0082 e 0083 e verifica schema/constraints; não se usa aqui o teste local ignorado como evidência de aprovação.
- O deploy registrou backup lógico, atualização `20261016_0082 → 20261017_0083`, publicação de `25cd338` e serviços Markina saudáveis. [Inventário 39049112709](https://github.com/conradodeita/markina-gallery/actions/runs/39049112709) confirmou revisão 0083 e HTTP 200 em `/healthz` e `/api/health`.
- A PR #214 (`c706679`) registra a evidência do probe e da publicação; seu CI de PR `39049217618` concluiu com sucesso. A alteração é documental e não requer repetir a migration ou o deploy funcional. O CI pós-merge `39051577413` ainda estava em andamento às 14:10 BRT; acompanhar seu resultado separadamente, sem declarar nova publicação.
- Retomada pelo chat sucessor autorizada pelo proprietário em 17/10/2026. Conferência SSH somente leitura às 14:07 BRT confirmou checkout remoto limpo em `25cd338`, todos os serviços Markina saudáveis, entrada exclusiva `127.0.0.1:8080` e resposta saudável em `/api/health`. Nenhum recurso, configuração, dado ou mensagem foi alterado nesta conferência.
- O primeiro acesso ao painel foi negado por falta de sessão administrativa. Após o proprietário liberar essa sessão, conferência visual autenticada em 17/10/2026 confirmou: Visão Geral com `Pastas com importação ativa = 0` e `0 fotos nas pastas ativas`; painel financeiro carregado sem o card `Falhas de mensagem`; evento `Novas fotos privadas` com Push e WhatsApp habilitados. Nenhum envio/salvamento foi executado. Capturas de tela permanecem somente no diretório local ignorado de diagnóstico; nenhuma imagem ou dado identificável de cliente integra este registro.

## Limites e pendências de revisão

### Atualização que substitui a avaliação funcional inicial

O proprietário iniciou um teste real de lote privado em 17/10/2026. Consulta em transação `READ ONLY` confirmou quatro fotos disponíveis, quatro jobs de mídia completos e pasta canônica restrita liberada; o lote permaneceu `closed`, sem `announced_at` e sem eventos/entregas. O worker geral saiu com código 1 às 17:17:51 UTC (sem OOM), com `sqlalchemy.exc.DataError` / `psycopg.errors.StringDataRightTruncation`: valor maior que `character varying(192)` no flush do evento. A chave textual composta tem 193 caracteres. Portanto, publicação/saúde anteriores e testes SQLite não comprovam a conclusão funcional deste cenário; a task 1.1 da change de produto foi reaberta. O registro abaixo é histórico e NÃO constitui aceite final após essa descoberta.

Não houve restart, edição de configuração, alteração de dados ou disparo manual por este executor. Correção/teste estão na própria change `fix-private-photo-notifications-and-admin-metrics`. O teste não tinha inscrição push ativa para o cliente no momento da consulta, embora o telefone estivesse verificado; essa condição foi informada ao proprietário separadamente. Nenhum nome, telefone, payload, chave ou mídia real entra neste artefato.

Na avaliação inicial, a implementação já estava instalada em homologação e foram reconciliadas as marcações com as evidências então existentes. O teste real posterior revelou a falha de chave acima; portanto, a conclusão funcional foi reaberta. A conferência deste executor não disparou WhatsApp/push nem comprova recebimento em um dispositivo. Os testes anteriores verificam criação/deduplicação/autorização e fronteiras de transporte simuladas. Nenhum resultado de produção é declarado.

Sincronização das specs principais e arquivamento permanecem sujeitos à revisão humana. A correção facial em andamento é outra change/PR e não foi publicada por esta reconciliação.
