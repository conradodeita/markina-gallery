# Design

## Context

Base: main 8dcb029954e0bc9b7b8188f2605f99cac45865fa. Run anterior 40397675011: backend 32min; pytest 1577 passed, 23 skipped em 1653.25s (27min41s incluindo shell). Os seis passos pytest anteriores repetem módulos/subconjuntos com as mesmas variáveis. O passo de concorrência posterior repete quatro testes e apenas exporta PHOTOGRAPHER_TEST_DATABASE_URL já definida no job. A exclusão posterior altera DATABASE_URL para PostgreSQL e NÃO é redundante: a suíte geral usa SQLite nesse contrato.

## Goals / Non-Goals

**Goals:** reduzir espera mantendo todos os testes coletados, integrações PostgreSQL, políticas de release e status backend estável. Demonstrar partição completa sem duplicatas.

**Non-Goals:** reduzir assertions, remover testes lentos, modificar fixtures/schema/produção, adiar cobertura crítica para nightly ou alterar a política aprovada de pushes/manuais completos.

## Decisions

- Três jobs `backend-tests`, cada qual com checkout, SQLite e dois serviços PostgreSQL exclusivos. Nunca usar processos concorrentes no mesmo banco. `fail-fast: false` permite medir e diagnosticar todas as partes.
- Cada runner coleta a suíte completa pelo pytest e distribui módulos inteiros por peso (quantidade de itens coletados), ordenando por peso decrescente e nome; escolhe sempre a parte com menor carga, com desempate pelo índice. Preservar ordem original dos itens na parte e os hooks de coleta/fixtures de sessão. Rejeitar coleção vazia, IDs duplicados, parâmetros inválidos ou partes vazias.
- Manifesto por parte com coleção completa, seleção, índice e quantidade de partes. O agregador exige todos os jobs bem-sucedidos, exatamente três manifestos, coleções idênticas e união das seleções igual à coleção, sem interseções. Falha, cancelamento, artefato ausente ou coleção divergente bloqueiam `backend` e os consumidores existentes.
- `backend-quality` executa instalação, lint e políticas de scripts uma vez. `backend` permanece como agregador de nome estável para os gates já existentes. Quando backend não for exigido pelo classificador, os três jobs podem ser skipped conforme o contrato existente.
- A regressão de exclusão com DATABASE_URL PostgreSQL executa uma única vez na primeira parte, depois da suíte. Manter ambas as variantes desse teste é cobertura distinta.
- JUnit, manifestos e `--durations=25` registram evidência datada por runner. Nenhuma redução percentual é afirmada antes da medição remota. Balanceamento por quantidade é aproximado; os tempos coletados permitem revisão futura se houver parte desproporcional.
- Não mudar a classificação de push/manual: a change optimize-dependabot-ci exige suíte completa antes de operações protegidas. Eliminar somente repetição e serialização desnecessária.

## Risks / Trade-offs

- Dependências implícitas entre módulos → coleta completa em cada parte; CI remoto comprova execução real antes de merge.
- Preparação repetida em três runners e eventual fila → medir tempo de parede e reconhecer overhead de minutos faturados; três runners é limite inicial explícito.
- Aprovação indevida por job ausente → agregador always condicionado ao escopo, checagem de resultados antes de baixar/verificar artefatos e testes negativos.
- A release 0090 usa main como suporte → publicar esta otimização em PR e manter a execução já iniciada intacta; coordenar integração antes de novo preflight para não invalidar SHA/fingerprint.

## Migration Plan

Validar planner, falhas de agregação, integração pytest sintética e contrato YAML; publicar PR e comparar CI remoto com baseline. Rollback via revert de PR, sem alterações de runtime. Sincronização/arquivo OpenSpec somente após revisão humana.
