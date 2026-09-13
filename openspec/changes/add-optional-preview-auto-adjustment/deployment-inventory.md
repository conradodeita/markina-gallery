# Inventário de publicação — 13/09/2026

## Escopo autorizado

O proprietário autorizou push, merge e deploy desta change em homologação mantendo o módulo desligado e confirmou explicitamente o plano após receber este inventário, inclusive sem iniciar o worker. Produção, ativação, processamento retroativo e avaliação de fotos reais não fazem parte desta publicação.

## Inventário somente-leitura

- Checkout `/opt/markina-gallery` limpo, SHA saudável `727b2e4f3f8775c75ba71b659e4404da99b51c13`, idêntico à base da branch local.
- Projeto `markina-gallery`, arquivo `docker/docker-compose.yml`, ambiente seguro `docker/.env.homolog` preservado.
- 12 serviços em execução saudáveis: nginx, web, api, worker, db, redis, três workers faciais e três serviços Evolution.
- Entrada exclusiva `127.0.0.1:8080`; subdomínio `https://markina-homolog.duckdns.org`. Web 3000/API 8000/PostgreSQL/Redis continuam internos.
- Disco: 194 GiB totais, 63 GiB usados, 132 GiB disponíveis, 33% ocupados.
- Redes Markina interna e acesso existente à npm-network preservados. Volumes de banco, Redis, mídias, referências faciais e Evolution preservados.
- Terceiros encontrados: Firefly/Clearbudget, Nginx Proxy Manager e Portainer. Nenhum container, rede, volume, porta, proxy, certificado ou configuração desses projetos será alterado.
- SSH somente-leitura usando chave de host já registrada para o IP resolvido do subdomínio; nenhuma chave de host nova aceita e nenhum segredo impresso.

## Plano de impacto zero sobre terceiros

1. Commit e PR para develop; gates existentes de backend/frontend/OpenSpec/gitleaks mantidos.
2. Pipeline protegido de homologação, com SHA exato e novo inventário imediatamente antes da publicação.
3. Backup lógico exclusivo do banco Markina; migration aditiva 0054 cria apenas preview_adjustment_settings e preview_adjustment, com enabled=false.
4. Atualizar os serviços da aplicação conforme script existente. Manter estado facial vigente true e integrações existentes, sem editar seus segredos.
5. Não iniciar o perfil/worker preview-adjustment: ele será provisionado antes do teste estético, sob escopo operacional próprio. Nenhum agendamento, backfill ou alteração de prévias existentes nesta entrega.
6. Confirmar SHA, migration head, saúde interna/externa, singleton desligado e fila vazia por consultas sem PII. Confirmar serviços de terceiros preservados.

Não executar down, prune, limpeza de fotos/clientes, downgrade ou restore. Em falha após migration, preservar as tabelas aditivas e revisar retorno de código ao SHA anterior; não reverter banco automaticamente. O pipeline permanece com seus gates; não se promete indisponibilidade zero dos próprios serviços Markina durante sua recriação.
