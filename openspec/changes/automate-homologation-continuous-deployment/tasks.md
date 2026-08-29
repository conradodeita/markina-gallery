## 1. Automação versionada de entrega

- [x] 1.1 Criar um script versionado de deploy que aceite somente um SHA explícito, confirme o diretório `/opt/markina-gallery`, o projeto Compose `markina-gallery` e um checkout limpo antes de qualquer alteração; verificar com testes de política/shell que diretórios ou projetos inesperados são recusados. (verificado por `bash scripts/test_deploy_homolog.sh` e `bash -n scripts/deploy-homolog.sh` em 2026-08-28)
- [x] 1.2 Adicionar ao workflow de CI um job `deploy-homolog` executado exclusivamente em push para `develop`, dependente de backend, frontend, OpenSpec e gitleaks aprovados, com Environment protegido; verificar a sintaxe do workflow e testes que confirmem gatilho, dependências e ausência de deploy após falha de CI. (verificado por `scripts/test_deploy_homolog_policy.py` e `prettier --check .github/workflows/ci.yml` em 2026-08-28)
- [x] 1.3 Fazer o job entregar apenas o SHA validado e parâmetros obtidos de GitHub Environment Secrets, sem imprimir ou persistir credenciais; verificar por inspeção automatizada que valores sensíveis não foram versionados e que os logs mascaram secrets. (verificado por `scripts/test_deploy_homolog_policy.py`; a varredura integral seguirá no job `gitleaks` do CI)

## 2. Publicação isolada e recuperação segura

- [x] 2.1 Implementar no script o registro do SHA saudável, backup lógico exclusivo da Markina, `alembic upgrade head`, reconstrução limitada aos serviços Markina e healthchecks/smoke tests; verificar em ambiente de teste controlado que um deploy saudável registra a revisão publicada. (run `33279596997`: backup lógico criado, migration construída no SHA alvo, Alembic `20260829_0014 (head)`, serviços saudáveis, SHA `751d746878aaad27885ba9297c88cf05ef5737f6` registrado e smokes externos 200 em 2026-08-29)
- [ ] 2.2 Implementar interrupção segura para checkout remoto sujo, migration falha ou healthcheck falho, com rollback somente de código/serviços Markina quando compatível e sem restauração automática do banco; verificar cenários simulados de falha e confirmar que nenhum recurso ClearBudget, proxy, DNS, firewall, rede ou volume de terceiros é acionado.
- [x] 2.3 Documentar bootstrap, inventário de impacto zero, procedimento de aprovação, rollback por SHA e limites de recuperação sem expor valores de secrets; verificar que a documentação identifica as configurações externas necessárias e não contém credenciais reais. (documentado em `docs/DEPLOY-CONTINUO-HOMOLOGACAO.md` e verificado pela política de secrets em 2026-08-28)

## 3. Ativação externa e validação de homologação

- [x] 3.1 Definir e configurar o GitHub Environment de homologação, com aprovador obrigatório e secrets de conexão, e instalar no servidor a credencial Git somente leitura; verificar a aprovação pendente no GitHub e acesso remoto autenticado sem expor chaves. (Environment público `homolog` configurado com aprovador `conradodeita`, proteção de branch e seis secrets; chaves dedicadas Actions→servidor e servidor→GitHub verificadas em 2026-08-28)
- [x] 3.2 Executar o bootstrap autorizado no servidor após inventário de `/opt/markina-gallery`, portas e subdomínio, confirmando origem GitHub, checkout limpo e isolamento do ClearBudget; verificar que nenhum serviço ou arquivo de outro projeto foi alterado. (origem GitHub somente leitura, `core.sshCommand` dedicado, diretórios `/var/lib/markina-gallery/{deploy-state,backups}` em modo 700, Compose/config e healthchecks aprovados; inventário Docker idêntico antes/depois em 2026-08-28)
- [ ] 3.3 Validar um deploy controlado de commit já aprovado em `develop`, confirmando SHA remoto, migrations aditivas, healthchecks externos e fluxo de rollback por SHA; registrar a evidência operacional sem versionar logs sensíveis.

## Registro de bloqueio — 2026-08-28

- As tarefas 2.1 e 2.2 têm a implementação versionada em `scripts/deploy-homolog.sh`, mas não podem ser marcadas como concluídas sem executar o deploy e os cenários controlados no servidor de homologação.
- As tarefas 3.1–3.3 exigem configuração externa do GitHub Environment `homolog`, secrets de SSH, chave Git de leitura no servidor e inventário aprovado de `/opt/markina-gallery`. Nenhum secret, `.env`, credencial, servidor ou recurso compartilhado foi modificado nesta execução.

## Atualização operacional — 2026-08-29

- O run `33278642428` recusou corretamente a execução fora de `/opt/markina-gallery`, antes de backup ou mutação. O run `33278955408` criou backup, selecionou somente o SHA Markina e interrompeu ao detectar o worker ausente; a investigação identificou e corrigiu a imagem de migration antiga. O run saudável `33279596997` comprovou a tarefa 2.1 e manteve todos os recursos fora do projeto Compose `markina-gallery` fora do escopo.
- A tarefa 2.2 permanece pendente porque o host compartilhado não foi submetido deliberadamente a uma migration falha nem a um rollback operacional real. A propagação sintética ao trap, a recusa de diretório inesperado e as proibições de recursos de terceiros passaram em `scripts/test_deploy_homolog.sh` e `scripts/test_deploy_homolog_policy.py`; a validação destrutiva real continua exigindo um ensaio humano controlado.
- A tarefa 3.3 permanece pendente apenas quanto à execução operacional do rollback por SHA. SHA remoto, migrations aditivas e healthchecks externos foram confirmados no run saudável acima; o procedimento e a seleção de SHA estão cobertos por política e documentação, mas nenhum rollback real foi provocado no host compartilhado.
