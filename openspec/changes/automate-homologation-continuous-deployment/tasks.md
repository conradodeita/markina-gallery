## 1. Automação versionada de entrega

- [x] 1.1 Criar um script versionado de deploy que aceite somente um SHA explícito, confirme o diretório `/opt/markina-gallery`, o projeto Compose `markina-gallery` e um checkout limpo antes de qualquer alteração; verificar com testes de política/shell que diretórios ou projetos inesperados são recusados. (verificado por `bash scripts/test_deploy_homolog.sh` e `bash -n scripts/deploy-homolog.sh` em 2026-08-28)
- [x] 1.2 Adicionar ao workflow de CI um job `deploy-homolog` executado exclusivamente em push para `develop`, dependente de backend, frontend, OpenSpec e gitleaks aprovados, com Environment protegido; verificar a sintaxe do workflow e testes que confirmem gatilho, dependências e ausência de deploy após falha de CI. (verificado por `scripts/test_deploy_homolog_policy.py` e `prettier --check .github/workflows/ci.yml` em 2026-08-28)
- [x] 1.3 Fazer o job entregar apenas o SHA validado e parâmetros obtidos de GitHub Environment Secrets, sem imprimir ou persistir credenciais; verificar por inspeção automatizada que valores sensíveis não foram versionados e que os logs mascaram secrets. (verificado por `scripts/test_deploy_homolog_policy.py`; a varredura integral seguirá no job `gitleaks` do CI)

## 2. Publicação isolada e recuperação segura

- [ ] 2.1 Implementar no script o registro do SHA saudável, backup lógico exclusivo da Markina, `alembic upgrade head`, reconstrução limitada aos serviços Markina e healthchecks/smoke tests; verificar em ambiente de teste controlado que um deploy saudável registra a revisão publicada.
- [ ] 2.2 Implementar interrupção segura para checkout remoto sujo, migration falha ou healthcheck falho, com rollback somente de código/serviços Markina quando compatível e sem restauração automática do banco; verificar cenários simulados de falha e confirmar que nenhum recurso ClearBudget, proxy, DNS, firewall, rede ou volume de terceiros é acionado.
- [x] 2.3 Documentar bootstrap, inventário de impacto zero, procedimento de aprovação, rollback por SHA e limites de recuperação sem expor valores de secrets; verificar que a documentação identifica as configurações externas necessárias e não contém credenciais reais. (documentado em `docs/DEPLOY-CONTINUO-HOMOLOGACAO.md` e verificado pela política de secrets em 2026-08-28)

## 3. Ativação externa e validação de homologação

- [ ] 3.1 Definir e configurar o GitHub Environment de homologação, com aprovador obrigatório e secrets de conexão, e instalar no servidor a credencial Git somente leitura; verificar a aprovação pendente no GitHub e acesso remoto autenticado sem expor chaves.
- [ ] 3.2 Executar o bootstrap autorizado no servidor após inventário de `/opt/markina-gallery`, portas e subdomínio, confirmando origem GitHub, checkout limpo e isolamento do ClearBudget; verificar que nenhum serviço ou arquivo de outro projeto foi alterado.
- [ ] 3.3 Validar um deploy controlado de commit já aprovado em `develop`, confirmando SHA remoto, migrations aditivas, healthchecks externos e fluxo de rollback por SHA; registrar a evidência operacional sem versionar logs sensíveis.

## Registro de bloqueio — 2026-08-28

- As tarefas 2.1 e 2.2 têm a implementação versionada em `scripts/deploy-homolog.sh`, mas não podem ser marcadas como concluídas sem executar o deploy e os cenários controlados no servidor de homologação.
- As tarefas 3.1–3.3 exigem configuração externa do GitHub Environment `homolog`, secrets de SSH, chave Git de leitura no servidor e inventário aprovado de `/opt/markina-gallery`. Nenhum secret, `.env`, credencial, servidor ou recurso compartilhado foi modificado nesta execução.
