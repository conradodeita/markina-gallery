# Proposal

## Why

O backend da PR #299 levou 32 minutos no run 40397675011: a suíte geral consumiu 27min41s e repetiu testes já executados em passos focados. O proprietário autorizou reduzir validações repetitivas e o tempo de espera, preservando a segurança do release.

## What Changes

- Executar a suíte completa do backend em três runners isolados, com partição determinística por módulo e confirmação de cobertura integral no check `backend`.
- Remover os passos pytest comprovadamente equivalentes à suíte completa, preservando a regressão adicional de exclusão que usa `DATABASE_URL` PostgreSQL.
- Executar lint e políticas de scripts uma única vez, em paralelo com os testes.
- Publicar tempos e relatórios por partição para medir a melhora e localizar os testes lentos.
- Preservar os nomes dos checks obrigatórios, classificação de PRs, validação completa de pushes/manuais, builds reais e gates de produção.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: testes completos distribuídos, agregação obrigatória e remoção de repetições somente com equivalência de configuração.

## Impact

Workflow CI, helper/testes da distribuição e documentação de engenharia. Nenhuma dependência nova nem alteração de aplicação, banco, permissões ou release remoto. A redução de tempo real depende dos runners e será medida no CI; mais runners simultâneos podem acrescentar overhead de preparação. O release 0090 mantém seu SHA e fluxo próprios.
