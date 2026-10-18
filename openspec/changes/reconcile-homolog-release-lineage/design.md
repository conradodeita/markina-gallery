# Design

## Estado observado

- O checkout de homologação e a versão de app identificada pelo inventário são `0779b3e4400f8511980c2d18e79ef8eea586a341`, merge de #207 em `main`.
- O banco está na revisão Alembic `20261016_0082`, correspondente a `facial_conditional_consent` nessa linha.
- `develop` deriva de `71be3b2` e a change #204 adicionou outra migration com revisão `20261016_0082`.
- O ambiente GitHub `homolog` exige revisor, mas aceita somente branches protegidas; `develop` não satisfaz a regra atual.
- O job de deploy falhou antes de iniciar, com a mensagem de que `develop` não está permitido. Nenhuma alteração remota foi executada.
- A CI integrada ao `main` executa uma política de release facial que fixa blobs de `backend/app/main.py` e `backend/app/auth.py`. A change privada altera esses arquivos apenas em rotas/modelos de upload e métricas, e não deve alterar a autorização do runtime facial.

## Decisões

- O commit alvo de homologação SHALL descend from `0779b3e`; assim o app não retrocede em relação ao inventário.
- A linha `main` observada será integrada a `develop` por PR. A change de produto permanece no mesmo PR/linha de desenvolvimento.
- A migration da pasta privada SHALL receber a próxima revisão única depois da revisão facial `20261016_0082`; o teste SHALL atualizar uma base já na revisão `0082` até a nova head.
- A elegibilidade de `develop` no ambiente será explícita e restrita à branch, mantendo a aprovação de reviewer existente. Nenhuma regra de `production` será alterada.
- O teste estático do gate facial SHALL rodar em PRs que têm `main` como destino e em pushes para `main`. PRs/pushes de `develop` continuam executando seus testes de homologação; a política de production permanece obrigatória antes de qualquer integração em `main`.
- O deploy SHALL continuar no fluxo CI existente após aprovação do ambiente; não haverá SSH manual, edição de dados, reset/clean do checkout ou parada ampla de containers.

## Verificações antes do deploy

- Confirmar que o merge alvo inclui `0779b3e` como ancestral.
- Validar a migration completa em PostgreSQL, partindo de `20261016_0082`.
- Executar CI integral e verificar que o job `deploy-homolog` chega ao gate de aprovação, sem aprová-lo antes de registrar o plano final de impacto zero.
- Repetir health checks públicos e inventário de containers após o deploy.
