## Why

Fotógrafo e cliente não conseguem confirmar visualmente qual identidade está ativa após entrar. Isso dificulta perceber uma conta ou número incorreto, especialmente em dispositivos compartilhados.

## What Changes

- Exibir nos cabeçalhos autenticados a identidade correspondente à sessão: e-mail do fotógrafo ou telefone da cliente.
- Obter a identidade exclusivamente do backend a partir da sessão autenticada.

## Capabilities

### Modified Capabilities

- `auth`: identificação visível da identidade autenticada nas áreas do fotógrafo e da cliente.

## Non-goals

- Não alterar login, OTP, autorização, troca de conta ou recuperação de acesso.
- Não mostrar dados de outra identidade nem incluir identidade em URLs ou armazenamento local.

## Impact

- Endpoint autenticado de identidade da sessão e cabeçalhos compartilhados do frontend.
