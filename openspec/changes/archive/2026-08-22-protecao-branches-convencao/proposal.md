## Why

O GitHub exige plano Pro para regras de proteção de branches em repositórios privados, e o proprietário decidiu manter o plano gratuito (projeto pessoal, sem intenção de venda). A spec `deployment-operations` precisa refletir o comportamento real: proteção da `main` por convenção e processo, sem enforcement técnico.

## What Changes

- Ajusta o requisito "Repositório com branches protegidas" da spec `deployment-operations` para o modelo por convenção: alterações na `main` somente via pull request com CI verde e revisão, mantendo `main` + `develop` + `feature/*` e Conventional Commits.
- Atualiza `README.md` (seção de convenções), `openspec/config.yaml` (linha de convenções) e `docs/DECISOES-TECNICAS.md` (decisão do plano gratuito).

## Capabilities

### New Capabilities

<!-- Nenhuma. -->

### Modified Capabilities

- `deployment-operations`: o requisito "Repositório com branches protegidas" passa a descrever proteção por convenção, sem enforcement técnico (pendente de plano GitHub compatível).

## Impact

- Apenas documentação e spec consolidada; nenhuma mudança de código ou de infraestrutura.
- Após aplicar e obter o aceite, a mudança será sincronizada em `openspec/specs/deployment-operations/` e arquivada.
