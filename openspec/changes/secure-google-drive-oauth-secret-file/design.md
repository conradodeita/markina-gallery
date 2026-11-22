# Design: Entrega protegida do segredo OAuth do Google Drive

## Decisão

- A API lê o objeto `web` do cliente OAuth em `/run/secrets/google-drive-oauth-client.json`.
- O arquivo deve ser regular, sem seguir symlinks, com modo POSIX `0400`; a implantação monta o arquivo host `/etc/pyp-google-drive/oauth-client.json` somente para leitura nesse caminho.
- O leitor aceita somente `client_id`, `client_secret` não vazios e exatamente uma `redirect_uri` HTTPS. Não registra conteúdo, exceções brutas ou material secreto.
- Em produção não existe fallback para `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET` ou `GOOGLE_DRIVE_REDIRECT_URI`; remover essas variáveis do container elimina a cópia em `.Config.Env`.
- A substituição é blue/green somente da API. A imagem e o container anterior sem as variáveis Drive permanecem como rollback; TOTP continua sendo carregado pelo procedimento validado. Nenhuma migration, escrita no banco, worker, proxy compartilhado ou chamada Drive faz parte desta change.

## Limite de segurança

O arquivo e a montagem reduzem exposição em metadata do Docker e a leitura casual por outros serviços. Um invasor com root no host, controle do daemon Docker ou execução de código dentro da API ainda pode acessar o segredo. A chave da aplicação usada para cifrar refresh tokens continua no contexto de runtime existente; ela não é alterada aqui.

## Evidência operacional inicial — 17/11/2026

- API `markina-gallery-api-1`, imagem `sha256:66771702d4cc6b4ef230a39f87464a9dfa439cbf97de8269d57c35ace4cbbeb1`, saudável; `APP_ENV=production` e `FACIAL_PROCESSING_ENABLED=true`.
- `/healthz`, `/api/health` e `/` responderam HTTP 200.
- O arquivo OAuth existe no host como `root:root`/`0400`, dentro de diretório `root:root`/`0700`, e contém a URI `https://markina.pickyourpic.com.br/api/admin/platform/drive/oauth/callback`.
- As três variáveis Drive estavam na configuração do container; o container `pyp-saas-drive-previous-api` preservado não contém variáveis `GOOGLE_DRIVE_*` e usa a mesma imagem saudável anterior.
- Nenhum consentimento foi concedido, refresh token ou job de backup foi criado, nem arquivo de cliente foi enviado.
