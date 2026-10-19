# Corrigir teste de imagem Nginx no monitoramento

## Why

O teste do relatório semanal exige a tag histórica `nginx:1.27-alpine` e reprova qualquer atualização válida da imagem, mesmo quando a configuração e a declaração do serviço continuam corretas.

## What Changes

- Validar a imagem declarada especificamente no serviço `nginx` do Docker Compose sem fixar uma versão.
- Exigir referência explícita ao repositório oficial `nginx` e tag numérica Alpine, preservando a política de evitar `latest`.
- Cobrir a declaração no Compose, o inventário de terceiros e o ecossistema Dependabot `docker-compose` em `/docker`.
- Acrescentar casos de teste para versões válidas e declarações ausentes ou incompatíveis com a política.

## Non-goals

- Não alterar a tag Nginx do Compose principal nem integrar o PR Dependabot #248.
- Não atualizar a produção, implantar serviços, executar migrations ou tocar na Oracle.
- Não alterar roteamento, configuração do proxy ou workflows de release/deploy.

## Impact

O teste de monitoramento passa a aceitar futuras tags numéricas Alpine válidas sem deixar de falhar se o serviço Nginx deixar de ser rastreável ou adotar referência inválida.
