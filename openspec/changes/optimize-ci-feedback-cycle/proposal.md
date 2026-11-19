# Proposal

## Why

Uma auditoria anterior reduziu o backend de cerca de 32 min para 8 min por meio de três shards, mas as CI recentes voltaram a um caminho crítico de até 31 min: o shard mais lento concentra módulos lentos e alterações de scripts fazem a matriz inteira rodar. A otimização precisa aproveitar resultados reais e selecionar somente validações seguras para PRs pequenos, sem reduzir a cobertura obrigatória nem afetar produção.

## What Changes

- Cancelar somente execuções obsoletas de CI de pull requests do mesmo PR; runs de push e dispatch terão grupos únicos e não serão cancelados por essa regra.
- Separar validações de qualidade da suíte de produto somente para a ferramenta read-only `scripts/ci_feedback.py` e seu teste; todos os demais scripts, caminhos críticos ou desconhecidos continuam executando a cobertura completa.
- Balancear os três shards existentes por duração histórica dos módulos, mantendo módulos/fixtures indivisíveis, cobertura integral e o check obrigatório `backend`.
- Retirar o deploy de `develop` e os workflows remotos de inventário, manutenção e rollout facial de homologação, preservando o ID legado do check obrigatório; atualizar documentação operacional e proteger a ausência com teste.
- Registrar medições observadas, projeções e limitações da amostra em `docs/CI-VALIDATION.md`; manter as releases de produção nas changes já existentes.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: seleção conservadora de validações em PR, distribuição de duração e cancelamento seguro de runs obsoletos.

## Impact

Workflows CI, `scripts/classify_ci_scope.py`, `scripts/backend_ci.py`, testes, pesos, documentação operacional e `docs/CI-VALIDATION.md`. Não altera APIs de produto, dados, migrations, secrets, configurações externas ou releases de produção. Pushes protegidos e operações manuais continuam com CI completo; aprovação humana e integridade dos artefatos permanecem nas changes de release existentes.
