# Inventário e plano do pacote capa, prévias e orientação OTP

## Autorização e escopo

O proprietário autorizou implementar todas as três alterações e solicitou explicitamente push, merge e deploy ao terminar. Inventário/plano apresentados no chat antes da publicação. Commits separados por change: fix-finalized-selection-purchase-previews, require-gallery-cover-in-details e clarify-client-otp-access-guidance. Entrega conjunta somente após CI do HEAD aprovado; preservar alterações documentais preexistentes da PR #144 fora dos commits.

## Preflight remoto — 08/10/2026

- Oracle 132.145.193.169, checkout /opt/markina-gallery limpo em af5b3a695f82a4493dcd7d99123da62599926633.
- Projeto markina-gallery, compose docker/docker-compose.yml, overlays próprios de branding e preview-adjustment existentes.
- Domínio https://markina-homolog.duckdns.org e porta própria 127.0.0.1:8080. healthz e api/health: HTTP 200.
- 13 serviços próprios saudáveis: api, web, worker, nginx, db, redis, evolution-api, evolution-db, evolution-redis, face-index-worker, face-search-worker, face-maintenance-worker e preview-adjustment-worker.
- Disco raiz: 108 GB disponíveis, 45% utilizado.
- Schema 20261001_0071; pacote não adiciona migration.
- Transação SQL READ ONLY: media_job 814 completed; facial_job 844 completed/8 cancelled; whatsapp_delivery 27 expired; gallery_lifecycle_operation vazio. Nenhum pendente/processando nessas filas; não prova ausência de upload iniciado depois da leitura.
- Terceiros inventariados para comparação posterior, sem alteração: firefly_bot 0237f8570ebc, firefly_frontend 704462c02602, firefly_api bba37a0fde01, firefly_db 768223c11835, nginx-proxy-manager 66c25ca56d8c e portainer e49166611a66.

## Plano de impacto

Merge em develop aciona CI e deploy-homolog existentes. Backup lógico próprio, build, preservação de branding e parada/recriação controlada de escritores próprios. Aplicação pode ficar temporariamente indisponível. Não prometer indisponibilidade zero. Impacto zero em terceiros: não tocar seus containers/imagens/redes/volumes/proxy/firewall/DNS/certificados.

Preservar fotos, clientes, fotógrafos, vínculos, pedidos, preferências, Evolution, e-mail e configurações; não configurar capas reais automaticamente. Não usar prune, compose down, exclusão de dados, trailers de limpeza ou alterações manuais de .env/secrets. Manutenção pós-deploy deve permanecer inventory. Schema deve permanecer 20261001_0071.

Antes de merge, reconferir CI/HEAD, base/remoto limpos e filas. Depois, verificar sucesso do job deploy, SHA remoto, hashes de código quando aplicável, saúde/endpoints e IDs de terceiros. CI de PR não comprova publicação. Se falhar, investigar/seguir rollback próprio previsto; nenhuma restauração de banco ou rotação de segredo implícita.

Aceite visual humano remoto posterior: upload/processamento de capa e avanço em Detalhes; Compras mostra miniaturas; OTP usa orientação neutra. Piloto A+B continua pendente, sem registrar teste com três clientes do mesmo fotógrafo como ensaio A+B. Limpeza fica para o final do roadmap.
