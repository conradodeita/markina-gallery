# Proposal

## Why

A primeira rodada concentrou nove PRs e dezenas de execuções de CI, incluindo atualizações incompatíveis agrupadas com atualizações ordinárias. O projeto precisa limitar a fila semanal, separar componentes especializados e executar testes somente nas áreas afetadas sem enfraquecer os checks obrigatórios da `main`.

## What Changes

- Limitar PRs ordinários a um por diretório/ecossistema do Dependabot, mantendo seis entradas de atualização e deixando atualizações de segurança sob a cadência própria do GitHub.
- Distribuir os seis ecossistemas ao longo da semana; agrupar somente famílias explicitamente compatíveis em patch/minor, deixando majors e motores críticos em PRs individuais.
- Classificar os arquivos de cada PR para selecionar testes backend, frontend, Gemma e motores fotográficos, mantendo sempre OpenSpec, Gitleaks e políticas de release.
- Usar o check obrigatório `homolog-inventory-policy` como agregador: qualquer escopo exigido que falhe, seja desconhecido ou não execute bloqueia o resultado.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations/external-dependency-monitoring`

## Impact

- `.github/dependabot.yml`, `.github/workflows/ci.yml` e um classificador de escopo local com testes unitários.
- Sem mudanças de dependências do produto, segredos, permissões de deploy, ambientes, banco de dados ou configuração Oracle.
- A configuração GitHub informa alerts e security updates desabilitados; habilitação depende do proprietário do repositório.
