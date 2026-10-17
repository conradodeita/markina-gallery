# Validação

## Estado inicial

- Ambiente GitHub `homolog`: regra `required_reviewers` com um usuário; `prevent_self_review=false`; política `protected_branches=true`.
- `develop` exige seis checks: `backend`, `frontend`, `gemma-runtime`, `openspec`, `homolog-inventory-policy` e `gitleaks`; force-push e exclusão estão proibidos.
- PR #213 foi integrada em `372a4a62e8eda505633fb8fc00fd30251be2b268`. Seu CI da PR `39054318967` passou integralmente. O CI pós-merge `39056806422` está em andamento.
- Inventário remoto: checkout `25cd338f7243a114e8151e6bda3d03204b12ae43`; `/api/health` HTTP 200; nginx publica somente `127.0.0.1:8080`; worker geral encerrado sem restart automático; outros serviços Markina e serviços Evolution compartilhados estavam saudáveis.
- A revisão Alembic `20261017_0083` foi confirmada na leitura anterior. Esta change não cria migration.

## Plano operacional

O job existente atua no projeto Compose `markina-gallery`, com backup e interrupção controlada dos escritores Markina antes de reiniciá-los. Pode haver breve indisponibilidade da aplicação. Não deve atingir containers, imagens, redes, volumes, proxy, firewall, DNS ou certificados de terceiros.

## Resultado

Em 17/10/2026, a regra `required_reviewers` foi removida do ambiente `homolog` via API. A leitura posterior confirmou somente `branch_policy`, com `protected_branches=true` e `custom_branch_policies=false`. Segredos e checks não foram alterados.

Pendente: conclusão do CI pós-merge `39056806422` e evidência de início/conclusão do deploy e healthchecks. Até este registro, backend e Gemma ainda estão executando; nenhuma publicação foi iniciada.

## Falha do primeiro deploy automático

O CI pós-merge `39056806422` terminou com backend e todos os demais checks verdes. O deploy iniciou automaticamente sem aprovação manual, mas o preflight falhou em `verify_facial_deploy_state`: `service "worker" is not running` / `worker diverge da configuração facial persistente`. A causa é que a checagem usa `compose exec` no container antigo, que está `exited (1)` pelo incidente confirmado da chave de 193 caracteres.

O log registra `publicação interrompida antes da preservação; containers antigos mantidos`. Portanto não houve troca de SHA, parada de serviços, migration ou perda do lote. A recuperação requer uma correção versionada e validada do preflight antes de novo deploy.

O preflight foi corrigido no worktree para aceitar apenas o container `worker` existente em `exited (1)`, cujos logs confirmam `value too long for type character varying(192)`, com configuração facial idêntica ao ambiente e SHA alvo contendo a correção da chave. Outros estados/códigos, erro divergente, container ausente, configuração diferente ou ausência do fix continuam bloqueados. A validação pós-deploy existente exige `worker` saudável. Testes de política positivos/negativos foram adicionados; aguardam CI.
