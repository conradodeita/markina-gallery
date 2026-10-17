# Tasks

- [x] 1.1 Registrar o inventário corrente, a regra `required_reviewers`, a política `protected_branches` e os checks de `develop` sem expor segredos. Evidência: ambiente `homolog` inicialmente com um revisor e `protected_branches=true`; branch `develop` com seis checks obrigatórios; inventário remoto registrado em `validation.md`.
- [x] 1.2 Remover somente o revisor obrigatório do ambiente `homolog`; preservar a restrição a branches protegidas, segredos e checks. Evidência: API do GitHub confirmou apenas `branch_policy` após atualização; política permanece `protected_branches=true`, `custom_branch_policies=false`.
- [ ] 1.3 Corrigir o preflight para permitir somente o worker existente em `exited (1)` quando os logs confirmam o erro `VARCHAR(192)`, o SHA alvo contém a correção de chave e sua configuração coincide com a persistida; proteger recusas de estados divergentes e a saúde pós-deploy.
- [ ] 1.4 Confirmar que o workflow inicia o deploy automaticamente após CI verde e que falhas de preflight continuam bloqueando a publicação.
- [ ] 1.5 Registrar SHA implantado, revisão Alembic, serviços Markina, portas, domínio e healthchecks depois da publicação automática.
- [ ] 1.6 Validar esta change em OpenSpec e registrar evidências sem sincronizar ou arquivar antes de revisão humana.
