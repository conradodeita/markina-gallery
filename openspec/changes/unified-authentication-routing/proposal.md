## Why

A Markina Gallery precisa de uma entrada simples para dois públicos sem misturar privilégios: o cliente deve chegar rapidamente à galeria autorizada, enquanto o fotógrafo deve passar por autenticação administrativa forte e ser encaminhado ao painel operacional.

## What Changes

- Criar uma única tela/rota de entrada para clientes e fotógrafo administrador.
- Oferecer na mesma tela o contexto de acesso correspondente, sem criar páginas de login separadas.
- Cliente: nome completo + telefone, seguido de código OTP enviado por WhatsApp.
- Fotógrafo: e-mail + senha, seguido de código TOTP do Google Authenticator/compatível.
- Redirecionar o fotógrafo autenticado para a área administrativa.
- Redirecionar o cliente autenticado para a galeria autorizada, ou para sua biblioteca quando houver mais de uma.
- Aplicar sessões, rate limit, respostas neutras e auditoria conforme o domínio `auth`.

## Capabilities

### New Capabilities

- `auth`: entrada unificada, autenticação do administrador e OTP do cliente.
- `client-access`: encaminhamento do cliente para galeria/biblioteca autorizada.

### Modified Capabilities

<!-- Nenhuma spec de domínio de produto foi sincronizada ainda. -->

## Impact

- Novo fluxo de autenticação e roteamento no frontend e backend.
- Sessões e permissões devem distinguir `admin` de `client` no servidor, nunca apenas no frontend.
- O acesso à galeria deve ser validado novamente no backend após o redirecionamento.
- A mudança não libera cadastro público de administrador nem altera a arquitetura de deploy.
