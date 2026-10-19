# Proposal

## Why

A manutenção do código diretamente afetado deve acompanhar cada funcionalidade e correção, com evidência e risco proporcional. Uma política permanente evita acumular código substituído sem criar auditorias gerais ou remoções artificiais.

## What Changes

- Estabelecer uma fonte única da política em `docs/CONTINUOUS-REFACTORING.md` e torná-la obrigatória por referência no `AGENTS.md`, inclusive fora de comandos OpenSpec.
- Acrescentar referências e orientações concisas em `context`, `rules.proposal`, `rules.tasks` e `operations.apply.guidance`, preservando as instruções existentes.
- Exigir avaliação proporcional do impacto no código existente, consumidores/compatibilidade, validação e registro do resultado; aceitar ausência de oportunidade elegível.
- Separar refatorações que ampliem significativamente risco/escopo, mantendo a funcionalidade prioritária e as autorizações existentes.

## Capabilities

### New Capabilities

Nenhuma capacidade de produto. A change declara `skip_specs: true` por alterar exclusivamente instruções e documentação de desenvolvimento.

### Modified Capabilities

Nenhuma. Contratos funcionais, financeiros, autenticação, isolamento de tenants e operação permanecem inalterados.

## Impact

Apenas `AGENTS.md`, `openspec/config.yaml`, a política e os artefatos desta change. Sem refatoração imediata, exclusão de arquivos, mudança funcional, dependências, CI/workflows, Oracle, deploy, migrations, dados ou limpeza. A verificação desta própria implementação não encontrou código elegível: seu escopo é exclusivamente documental. Integração condicionada a revisão, checks e segurança dos gatilhos.
