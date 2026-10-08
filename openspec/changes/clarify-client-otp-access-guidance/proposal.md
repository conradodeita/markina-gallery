# Proposal

## Why

O teste humano da PR #144 confirmou a supressão de OTP para telefone sem vínculo em convite individual. A interface ainda afirma que o código foi enviado, criando expectativa incorreta. O proprietário aprovou orientação condicional idêntica para todas as clientes.

## What Changes

- Exibir após solicitação e reenvio bem-sucedidos: “O código será enviado somente se este telefone tiver acesso à galeria. Se não receber, confirme seu acesso com o fotógrafo.”
- Usar o rótulo “Código de acesso”, conservando o campo e a resposta neutra.
- Preservar autenticação, elegibilidade, payloads, rate limit e fluxo administrativo.

## Capabilities

### New Capabilities

### Modified Capabilities

- `auth`: orientação neutra após solicitar/reenviar OTP de cliente.

## Impact

Frontend de entrada e regressões. Sem migration, envio adicional ou divulgação de vínculo. Implementação, push, merge e deploy deste pacote autorizados pelo proprietário em 08/10/2026; inventário e CI continuam obrigatórios.
