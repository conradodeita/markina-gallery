# Proposta: Publicar automaticamente em homologação após CI

## Problema

O CI de `develop` termina os checks de código, mas o deploy fica parado aguardando um revisor manual no ambiente `homolog`. O merge já é protegido pelos checks obrigatórios; repetir uma autorização por execução alonga a recuperação de falhas e exige acompanhamento manual.

## Mudança proposta

O deploy de homologação SHALL iniciar automaticamente após os checks obrigatórios do push em `develop` passarem. A restrição do ambiente a branches protegidas, os checks obrigatórios, o inventário/preflight, o backup, o escopo exclusivo de `markina-gallery` e os healthchecks SHALL permanecer ativos. A aprovação humana por execução será removida somente do ambiente `homolog`.

## Não objetivos

- Não remover proteção ou checks da branch `develop`.
- Não automatizar publicação em produção.
- Não alterar segredos, banco, migrations ou recursos de outros projetos.

## Impacto

Cada merge em `develop` poderá publicar automaticamente em homologação após CI. O fluxo existente pode interromper brevemente os serviços da Markina enquanto atualiza imagens e workers. Recursos de terceiros permanecem fora do escopo.
