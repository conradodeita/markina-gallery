# Proposal

## Why

O teste humano da PR #144 confirmou a supressão de OTP para telefone sem vínculo em convite individual. A interface ainda afirma que o código foi enviado, criando expectativa incorreta. O proprietário aprovou orientação condicional idêntica para todas as clientes.

## What Changes

- Exibir na etapa de validação após solicitação e reenvio aceitos: “O código será enviado somente se este telefone tiver acesso à galeria. Se não receber, confirme seu acesso com o fotógrafo.”
- Usar o rótulo “Código de acesso”, conservando a resposta neutra. Para `invite_only`, o change `show-private-gallery-access-guidance` apresenta primeiro o aviso privado e só abre esta etapa após a ação explícita da cliente.
- Preservar autenticação, elegibilidade, payloads, rate limit e fluxo administrativo.

## Capabilities

### New Capabilities

### Modified Capabilities

- `auth`: orientação neutra após solicitar/reenviar OTP de cliente.

## Impact

Frontend de entrada e regressões. Sem migration, envio adicional ou divulgação de vínculo. Implementação, push, merge e deploy deste pacote autorizados pelo proprietário em 08/10/2026; inventário e CI continuam obrigatórios.
