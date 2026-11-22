# Proposal: Entrega protegida do segredo OAuth do Google Drive

## Contexto

O runtime atual recebe `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET` e `GOOGLE_DRIVE_REDIRECT_URI` no ambiente configurado do container da API. O segredo fica consultável por quem tem acesso administrativo ao Docker. O host já guarda o JSON do cliente Web em `/etc/pyp-google-drive/oauth-client.json`, com diretório `root:root`/`0700` e arquivo `root:root`/`0400`.

## Goals

- Fazer a API ler o cliente OAuth Web diretamente de um arquivo secreto montado somente para ela e em modo somente leitura.
- Remover as três variáveis `GOOGLE_DRIVE_*` da configuração persistida do container.
- Falhar de forma fechada quando o arquivo estiver ausente, permissivo, inválido ou pedir mais de uma URI de retorno.
- Preservar o fluxo OAuth, `drive.file`, o estado de produção e todas as demais configurações do serviço.

## Non-goals

- Conceder consentimento Google, iniciar uploads, executar backups ou ler arquivos de clientes.
- Alterar a chaveiro TOTP, outros segredos, banco, schema, workers, proxy público ou configuração de outros serviços.
- Tratar acesso root ao host ou ao daemon Docker como fora do limite de confiança.
