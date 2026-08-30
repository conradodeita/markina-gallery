## Context

O repositório possui CI para pull requests e pushes em `develop`, mas não possui job de deploy. A homologação da Markina Gallery roda isoladamente em `/opt/markina-gallery`; seu checkout ainda foi atualizado por bundles manuais e o acesso SSH local atual não é aceito. Consulte `proposal.md` para a motivação e a delta spec para o contrato de publicação.

## Goals / Non-Goals

**Goals:**

- Tornar `develop` a única origem de deploy em homologação após CI verde.
- Usar GitHub Environment protegido para a aprovação humana de homologação.
- Implantar e registrar um SHA verificável, com rollback limitado à Markina Gallery.
- Bloquear o deploy se o servidor ou checkout não estiverem no estado seguro esperado.

**Non-Goals:**

- Não automatizar produção, alterar secrets existentes, provisionar proxy, DNS, certificados ou infraestrutura de outros projetos.
- Não publicar branches feature, commits sem CI verde ou alterações não commitadas.
- Não apagar banco, volumes, imagens ou dados para realizar deploy.

## Decisions

### GitHub Actions como orquestrador pós-CI

Um job `deploy-homolog` será adicionado ao workflow existente, acionado apenas em push para `develop` e dependente dos jobs backend, frontend, OpenSpec e gitleaks. Ele usará o Environment `homolog`, que deve exigir aprovação humana no GitHub antes da conexão SSH.

Alternativa descartada: deploy a cada push de feature. Isso quebra a revisão por CI/PR e não oferece uma referência integrada estável.

### Checkout remoto por SHA e origem GitHub somente leitura

O bootstrap único do servidor trocará a origem do checkout da Markina para o repositório GitHub e instalará uma credencial de leitura restrita no próprio servidor. O workflow enviará o SHA validado; no host, o script fará `fetch`, verificará que o checkout está limpo e selecionará exatamente esse SHA. O processo aborta em vez de sobrescrever mudanças remotas.

Alternativa descartada: continuar transferindo bundles manuais. Embora o bundle contenha commits, ele não mantém uma origem única rastreável e torna a automação e a auditoria frágeis.

### Script de deploy versionado, secrets externos

O workflow chamará um script versionado no repositório para executar checagens, backup lógico exclusivo, `alembic upgrade head`, reconstrução dos serviços Markina necessários e smoke tests. Host, usuário, porta SSH, chave privada e fingerprint ficarão em secrets do Environment. O script nunca lê nem modifica `docker/.env.homolog` fora do uso pelo Compose.

Alternativa descartada: colocar comandos longos e credenciais no YAML do workflow. Isso dificulta revisão, rollback e proteção contra vazamento.

### Rollback sem restauração automática de banco

Antes da migration, o script registra o SHA saudável e cria backup lógico exclusivo da Markina. Em falha, o rollback automático só volta os serviços ao SHA anterior quando a migration não tornou o schema incompatível. Restauração do banco permanece ação humana explícita.

Alternativa descartada: restaurar banco automaticamente. É uma operação irreversível e pode apagar dados de homologação úteis para revisão.

## Risks / Trade-offs

- [Acesso SSH e credencial Git não configurados] → o workflow falha fechado antes de conectar; bootstrap é uma tarefa humana única e auditável.
- [Checkout remoto contém alteração manual] → abortar antes de `fetch`/troca de SHA e solicitar reconciliação humana.
- [Migration aditiva falha] → manter backup, parar e não executar rollback de banco automaticamente.
- [Falha de healthcheck após troca de código] → voltar somente os serviços Markina ao SHA saudável e registrar a falha.
- [ClearBudget compartilhando o host] → validar explicitamente projeto, diretório, serviços e portas antes de qualquer Compose.

## Migration Plan

1. Criar workflow e script, com validação local e revisão do YAML.
2. Criar Environment `homolog` no GitHub, configurar aprovação e secrets; instalar no servidor a chave Git de leitura e restaurar acesso administrativo SSH.
3. Executar bootstrap somente após inventário de impacto zero aprovado; confirmar checkout limpo e backup exclusivo da Markina.
4. Fazer um deploy manual disparado pelo GitHub de um SHA já aprovado, validar healthchecks e registrar versão/rollback.
5. Habilitar o gatilho automático em `develop` após o primeiro deploy controlado bem-sucedido.

## Open Questions

- O nome final do GitHub Environment será `homolog` ou `homologacao`; a implementação assumirá `homolog` até a configuração ser criada, pois esse nome não altera o contrato de deploy.
