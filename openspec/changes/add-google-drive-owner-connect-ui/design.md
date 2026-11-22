# Design: Interface de conexão do Google Drive do proprietário

## Contrato

- A página `/admin/platform` continua sendo o ponto de entrada e já é restrita ao proprietário.
- O formulário aparece quando não há conexão ativa (`unknown`, `revoked` ou `reauthorization_required`); não aparece para estado `connected`.
- O navegador envia `current_password` e `totp_code` por `POST` JSON para uma rota same-origin dedicada. A rota mantém `require_same_origin`, `_owner`, rate limit e reautenticação já usados por `/connect`.
- A nova resposta JSON contém somente `authorization_url`; o endpoint existente `/connect` mantém o comportamento 303 para compatibilidade.
- O frontend aceita somente HTTPS em `accounts.google.com`, no caminho `/o/oauth2/v2/auth`, e confirma que o parâmetro `scope` é exatamente `https://www.googleapis.com/auth/drive.file` antes de navegar.
- O backend continua responsável por criar state, verifier PKCE cifrado, tentativa curta e evento de auditoria. Client secret, verifier e refresh token nunca são enviados ao frontend.
- Os campos de senha/TOTP são limpos imediatamente após o envio. A resposta e a requisição usam cache `no-store`; erros são neutros.

## Caminho do usuário

1. O proprietário autenticado abre `Plataforma` e escolhe conectar Google Drive.
2. Digita novamente sua senha e o TOTP atual e envia o formulário.
3. Se reautenticação e controles owner-only passarem, o frontend valida a URL retornada e redireciona para o Google.
4. O fluxo termina na tela Google. Somente o proprietário pode aprovar o consentimento; nenhuma ação automatizada seleciona essa aprovação.

## Segurança e limites operacionais

- O body contém somente dados de reautenticação e é processado pela rota `SensitiveRoute`, com limite de tamanho e `Cache-Control: private, no-store`.
- A tentativa OAuth cria um registro temporário e consome o passo TOTP. Não há conexão ativa até um callback Google válido com refresh token e escopo exato.
- A navegação fora do endpoint Google permitido falha fechada.
- A interface não consulta quota nem inicia uso de Drive.

## Manutenção contínua

A interface existente de fontes continua necessária para exibir estado e quota; ela não é substituída. O comportamento novo será isolado em um componente pequeno e testado. Não há oportunidade segura para remover ou reorganizar código existente.
