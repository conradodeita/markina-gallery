## Why

O fluxo atual valida código no GitHub, mas não publica automaticamente uma revisão validada em homologação. O servidor ainda recebe atualizações manuais por bundle, o que permite divergência entre o commit local, o GitHub e o ambiente de teste.

## What Changes

- Fazer o GitHub Actions publicar em homologação somente após todos os jobs de CI aprovarem um commit integrado em `develop`.
- Exigir aprovação do ambiente de homologação e usar exclusivamente secrets do GitHub para acesso SSH, host e verificação do servidor.
- Trocar o mecanismo manual de bundle por uma revisão Git identificável no servidor, registrar o SHA implantado e executar migrations aditivas, reconstrução limitada aos serviços Markina e smoke tests.
- Documentar o procedimento de bootstrap de acesso e o rollback por SHA, sem versionar chaves, segredos ou arquivos `.env`.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: homologação passa a ter entrega contínua rastreável, protegida por CI verde, aprovação explícita e verificações pós-deploy.

## Impact

- `.github/workflows/` e documentação operacional de deploy/rollback.
- Configuração externa única no GitHub (Environment e secrets) e no servidor de homologação para acesso Git somente leitura.
- Servidor `/opt/markina-gallery`, limitado ao projeto Docker Compose `markina-gallery`; não altera ClearBudget, Proxy Manager, DNS, firewall, certificados, redes ou volumes de terceiros.
