# Operação: Entrega protegida do segredo OAuth do Google Drive

## Inventário e retorno

- Escopo de runtime: somente a API `markina-gallery-api-1` em `markina-gallery_internal`; não alterar web, workers, PostgreSQL, Redis, Evolution, Nginx Manager ou qualquer outro projeto do host.
- Antes da troca, validar imagem base, saúde da API, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, presença das variáveis antigas apenas por nome, arquivo OAuth `root:root`/`0400` no diretório `root:root`/`0700`, e HTTP 200 em `/healthz`, `/api/health` e `/`.
- Construir uma camada pequena sobre o digest da imagem API que já está ativo. Copiar somente `app/google_drive_oauth.py` e o teste correspondente; não reconstruir dependências sem pin nem incorporar atualizações alheias.
- Criar candidato clonando a configuração atual, removendo do ambiente as três variáveis `GOOGLE_DRIVE_*`, restaurando TOTP exclusivamente pelo loader validado e montando o JSON host em `/run/secrets/google-drive-oauth-client.json` como bind read-only. Comparar a configuração sem imprimir valores.
- Antes de alterar tráfego, exigir candidato saudável, leitura sintética local do módulo de configuração, escopo/URI exatos, mount read-only e confirmação de que nenhum valor de client ID/secret foi escrito em log.
- Roteamento blue/green deve preservar o inode do arquivo Nginx bind-mounted, validar `nginx -t`, drenar workers antigos e confirmar endpoints públicos. Se houver falha, retornar a rota para o API anterior e iniciar o container de rollback sem variáveis Drive.
- Após a promoção saudável, remover somente o container API substituído que ainda conserva o segredo no metadata. Não usar `-v`; preservar o container `pyp-saas-drive-previous-api`, imagens e volumes.

## Estado externo e limites

O consentimento Google continua pendente. Esta operação não chama endpoints OAuth/Drive, não lê/escreve mídia ou banco, não inicia backup e não altera permissões de contas. A permissão do host root/daemon Docker permanece dentro da fronteira de confiança.
