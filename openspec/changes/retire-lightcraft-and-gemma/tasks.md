# Tasks

## 1. Inventário e contrato

- [x] 1.1 Confirmar o HEAD base `4cc02068`, o head Alembic `20261025_0089` e os consumidores RAW/Gemma em backend, frontend, Compose, ferramentas de homologação, monitoramento de terceiros e CI; registrar no OpenSpec que runtime remoto posterior a 19/10 não foi confirmado. Evidência: `git rev-parse HEAD` → `4cc020680a4a496801f4e36b3e0a737db2fc67c5`; `alembic heads` → `20261025_0089 (head)`; buscas delimitadas no código rastreado em 26/10/2026. O checkout original sujo permaneceu intocado; runtime remoto não foi consultado.
- [x] 1.2 Validar os deltas OpenSpec contra as specs consolidadas e confirmar que a proposta mantém o ajuste de prévias e o fluxo facial SFace; executar `openspec validate retire-lightcraft-and-gemma --strict` → `Change 'retire-lightcraft-and-gemma' is valid`.

## 2. Encerrar admissão e processamento RAW

- [x] 2.1 Remover rotas, validação, modelos e ramificações de upload RAW e manter o contrato JPEG; regressão backend `test_folder_upload_accepts_only_preparing_jpeg_and_reports_file_state` passou (1 teste), cobrindo 415 para conteúdo não JPEG e caminho JPEG. Vitest dos arquivos de upload/editor/monitor passou (89 testes).
- [x] 2.2 Remover UI/seleção RAW, worker, adaptadores, Dockerfile, override Compose, configuração Nginx e testes exclusivos; `docker compose -p markina-gallery -f docker/docker-compose.yml config --quiet` passou. Overrides/rotas/worker e limites específicos foram removidos. Referências remanescentes são guardas/inventário de runtime legado ou preservação de dados e estão documentadas; migrations e arquivos não foram apagados.

## 3. Aposentar EmbeddingGemma

- [x] 3.1 Remover seletor/admin API, provider/assets, roteamento, tipos de novos jobs, métricas e testes exclusivos; regressões faciais passaram (56 testes). Busca e indexação continuam fixas em SFace, e jobs Gemma legados não são admitidos para execução.
- [x] 3.2 Remover imagem, dependências PyTorch/Transformers, serviço/profile Compose, scripts e gates `gemma-runtime` do CI/agregadores; testes focados passaram: escopo CI (10), agregador (6), inventário de terceiros (11), dependências (19), pin especializado (2), políticas de homologação e retomada. Configuração Compose normal validada.
- [x] 3.3 Migrations e rotinas de preservação mantêm settings, embeddings, jobs e buscas legadas sem reescrita; constraints ORM continuam compatíveis. `alembic heads` → `20261025_0089 (head)`; nenhuma migration nova ou destrutiva foi criada.

## 4. Manter RawTherapee no ajuste de prévias

- [ ] 4.1 Fixar RawTherapee 5.13 no Dockerfile do worker opcional usando artefatos oficiais e SHA-256 por arquitetura; builds x86_64/ARM64 e smoke headless foram incluídos no CI. A execução local foi evitada por compartilhar o Docker host com outros projetos; aguarda evidência do CI.
- [ ] 4.2 Atualizar documentação do worker, licença/origem e inventário de terceiros com versão, checksums, consumidores e limites do smoke; a documentação foi atualizada e o job `runtime-images` executará os comandos após push, ainda pendente de CI.

## 5. Integração e continuidade

- [x] 5.1 Atualizar roadmap, instruções e documentação de operação para registrar JPEG-only, SFace-only e RawTherapee 5.13; inventários/runbooks históricos agora estão identificados como snapshots e os guardas/dados legados têm finalidade documentada.
- [x] 5.2 Regressões focadas, lint, typecheck e build locais: facial 56 testes; teste de upload backend 1; Vitest completo 550 testes/64 arquivos; ESLint sem erros; `next build` com TypeScript passou; Compose principal passou. `npx -y @fission-ai/openspec@1.14.0 validate --strict --all` (versão do CI) passou 140/140. A versão local 1.14.1 sinalizou 31 warnings antigos como falhas; CI usa 1.14.0. Builds do worker em ambas as arquiteturas aguardam o job runtime-images.
- [x] 5.3 Revisar diff e busca residual: não há provider, endpoints, UI, dependências ou serviços executáveis RAW/Gemma. Referências remanescentes estão restritas a constraints/ORM e migrations históricas, inventário/limpeza de staging, guardas que bloqueiam runtime legado e runbooks snapshots. O checkout original continua com os mesmos 160 itens sujos e não foi alterado; `git diff --check`, `compileall` e busca residual foram concluídos.
- [ ] 5.4 Após validação local, criar commit e push da branch desta change, abrir PR e conferir CI a cada 30 minutos até os checks exigidos terminarem; não fazer merge ou deploy.

## Workflow follow-up

- Antes de release, atualizar o inventário remoto de schema, ambiente, serviços/imagens ativos, filas/jobs RAW/Gemma, embeddings e volumes staging. A observação de 19/10 é histórica e o schema 0089 informado pelo proprietário não comprova estado de containers.
- Parada/recriação de workers, limpeza de imagens, exclusão de dados/volumes, migration ou deploy exigem plano de impacto zero e autorização operacional específica. Manter a change não arquivada até revisão humana e reconciliação do inventário de runtime.
- Após CI verde e revisão humana, sincronizar as specs principais e arquivar a change pelo fluxo OpenSpec.
