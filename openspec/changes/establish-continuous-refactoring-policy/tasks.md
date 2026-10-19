# Tasks

## 1. Política permanente e alcance

- [x] 1.1 Registrar a política única em docs/CONTINUOUS-REFACTORING.md, contemplando todas as regras aprovadas; verificar cobertura por revisão documental e limites de escopo.
- [x] 1.2 Referenciar a política obrigatoriamente no AGENTS.md da raiz para implementações com ou sem comando OpenSpec; conferir link e preservação das regras preexistentes.

## 2. Integração OpenSpec

- [x] 2.1 Acrescentar referências concisas a context, rules.proposal, rules.tasks e operations.apply.guidance sem remover instruções existentes; verificar parsing e saída efetiva de instructions nas versões 1.14.1 instalada e 1.14.0 do CI.
- [x] 2.2 Registrar a avaliação proporcional desta implementação: não há código funcional substituído/obsoleto elegível no escopo documental; revisar diff, links e confirmar ausência de remoções artificiais ou mudanças em produto/ambientes.

## 3. Validação e segurança de integração

- [x] 3.1 Validar a change e o conjunto OpenSpec estritamente, além de git diff --check; registrar resultados reproduzíveis em validation.md.
- [ ] 3.2 Revisar o diff final e gatilhos diretos/indiretos de CI; classificar o commit como release_scope=none e preparar PR exclusivamente de instruções/documentação, sem bypass, alteração de workflows ou operação real.

## Workflow follow-up

- Publicar PR para main e integrar somente com checks/revisões exigidos e segurança dos gatilhos confirmados. Resultados de CI e merge ficam no próprio PR/GitHub, sem marcar validação futura como concluída por previsão.
- Não sincronizar/arquivar specs funcionais sem revisão humana; esta change de tooling não modifica comportamento de produto nem inicia refatoração imediata.
