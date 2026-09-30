# Proposal

## Why

Quando a exclusão administrativa falha antes de concluir, a interface mostra apenas uma mensagem genérica e não permite distinguir bloqueio esperado, erro HTTP ou falha inesperada. Um código de atendimento ligado a log sanitizado permitirá diagnosticar futuras tentativas sem registrar dados pessoais ou contornar as proteções transacionais.

## What Changes

- Emitir um identificador aleatório de diagnóstico por tentativa de exclusão de cliente e incluí-lo em respostas de falha inesperada.
- Registrar esse identificador com categoria técnica segura e resultado da transação, sem identidade, telefone, payload, SQL ou mensagem bruta da exceção.
- Apresentar ao fotógrafo uma mensagem curta com o identificador para suporte; preservar as respostas e inventários existentes para bloqueios comerciais e validações conhecidas.
- Manter a operação idempotente e transacional. O evento de auditoria referencia o recibo persistido em vez de duplicar contagens longas; o recibo continua guardando os dados completos da operação.

## Capabilities

### New Capabilities

- `client-access/client-lifecycle-diagnostics`: código de atendimento e diagnóstico sanitizado para falhas inesperadas no lifecycle administrativo de cliente.

### Modified Capabilities

- `client-access/admin-client-directory`: manter a auditoria da exclusão compatível com o limite de armazenamento PostgreSQL.

## Impact

- Backend FastAPI: tratamento e log estruturado da rota administrativa de exclusão, com rollback verificado antes de classificar a falha como não concluída.
- Frontend Next.js: interpretação do contrato de erro e apresentação acessível do código de atendimento sem expor detalhes internos.
- Testes: falhas mapeadas, falhas inesperadas antes/depois do commit, ausência de PII/SQL no corpo e log, e preservação de respostas comerciais conhecidas.
- Nenhuma alteração de schema, credenciais, configuração do servidor, infraestrutura ou categorias de dados removidos é prevista.
