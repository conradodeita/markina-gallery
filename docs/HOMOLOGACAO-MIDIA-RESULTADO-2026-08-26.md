# Resultado da homologação — prévias protegidas (2026-08-26)

## Escopo aplicado

- Commit homologado: `94dd74d` (`feat(media): deliver protected preview workflows`).
- Stack atualizada somente em `/opt/markina-gallery`, com `docker compose -p markina-gallery`.
- Serviços recriados: `web`, `api`, `worker`, `migrate` e, para renovar a resolução interna do novo container de API, somente o `nginx` da Markina.
- Serviços do ClearBudget, Nginx Proxy Manager e Portainer não foram alterados.

## Isolamento confirmado

- O Nginx da Markina permanece publicado apenas em `127.0.0.1:8080` e acessado externamente pelo host HTTPS já existente `markina-homolog.duckdns.org`.
- Foram criados apenas os volumes `markina-gallery_media-source` e `markina-gallery_media-derivatives`.
- Banco, Redis e os novos volumes têm prefixo `markina-gallery_`; nenhum volume, rede ou container do ClearBudget foi modificado ou removido.

## Validações aprovadas

- Migration `20260826_0003` concluída com sucesso (container `migrate`, saída zero).
- Containers `api`, `web`, `worker`, `db`, `redis` e `nginx` saudáveis.
- Smoke tests interno e externo aprovados em `/healthz` e `/api/health`.
- Imagem JPEG inteiramente sintética criada no volume privado; o worker gerou `thumbnail`, `client_preview` e `admin_preview`.
- As prévias verificadas não continham EXIF, respeitaram o limite de resolução e a prévia da cliente diferiu da prévia administrativa.
- O registro, o JPEG sintético, seus derivados e os pacotes temporários de transferência foram removidos após a verificação.

## Observação operacional

Após recriar `api`, o Nginx da Markina manteve o endereço interno anterior e retornou 502 em `/api/health`. A recriação exclusiva de `markina-gallery-nginx-1` renovou essa resolução; nenhum serviço externo foi reiniciado. Os healthchecks voltaram a verde.
