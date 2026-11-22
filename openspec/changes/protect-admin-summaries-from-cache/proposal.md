# Proposal

## Why

Resumos administrativos retornam dados associados à conta autenticada, incluindo a identidade mascarada do fotógrafo e nomes de clientes com seleção recente. Essas respostas precisam ser explicitamente excluídas do cache HTTP para reduzir a permanência de dados pessoais no navegador ou em intermediários.

## What Changes

- Definir resposta `private, no-store` para os resumos administrativos de segurança e de atividade operacional.
- Verificar os cabeçalhos em testes de contrato autenticados, preservando as respostas e o escopo atuais.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `auth`: respostas do resumo de segurança administrativa não podem ser armazenadas em cache.
- `gallery-sales/operational-gallery-interface`: o resumo de atividade recente com nomes de clientes não pode ser armazenado em cache.

## Impact

- Rotas `GET /admin/security/summary` e `GET /admin/validation-summary` em `backend/app/main.py`.
- Testes de contrato backend para cabeçalho e respostas autenticadas.
- Nenhuma mudança no formato JSON, no frontend, banco, migrations, serviços externos ou produção.
