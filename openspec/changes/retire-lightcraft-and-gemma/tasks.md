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

- [ ] 4.1 Fixar RawTherapee 5.13 no Dockerfile do worker opcional usando artefatos oficiais e SHA-256 por arquitetura; builds x86_64/ARM64 e smoke headless estão no CI. Após corrigir `libexpat1` e a chamada CLI, build e smoke AMD64 passaram localmente em ambiente isolado; detalhes em Workflow follow-up. Evidência ARM64 e CI completo ainda pendentes.
- [ ] 4.2 Atualizar documentação do worker, licença/origem e inventário de terceiros com versão, checksums, consumidores e limites do smoke; a documentação foi atualizada e o job `runtime-images` executará os comandos após push, ainda pendente de CI.

## 5. Integração e continuidade

- [x] 5.1 Atualizar roadmap, instruções e documentação de operação para registrar JPEG-only, SFace-only e RawTherapee 5.13; inventários/runbooks históricos agora estão identificados como snapshots e os guardas/dados legados têm finalidade documentada.
- [x] 5.2 Regressões focadas, lint, typecheck e build locais: facial 56 testes; teste de upload backend 1; Vitest completo 550 testes/64 arquivos; ESLint sem erros; `next build` com TypeScript passou; Compose principal passou. `npx -y @fission-ai/openspec@1.14.0 validate --strict --all` (versão do CI) passou 140/140. A versão local 1.14.1 sinalizou 31 warnings antigos como falhas; CI usa 1.14.0. Builds do worker em ambas as arquiteturas aguardam o job runtime-images.
- [x] 5.3 Revisar diff e busca residual: não há provider, endpoints, UI, dependências ou serviços executáveis RAW/Gemma. Referências remanescentes estão restritas a constraints/ORM e migrations históricas, inventário/limpeza de staging, guardas que bloqueiam runtime legado e runbooks snapshots. O checkout original continua com os mesmos 160 itens sujos e não foi alterado; `git diff --check`, `compileall` e busca residual foram concluídos.
- [ ] 5.4 Após validação local, criar commit e push da branch desta change, abrir PR e conferir CI a cada 30 minutos até os checks exigidos terminarem; não fazer merge ou deploy.

## Workflow follow-up

### Correção dos checks da PR #292 — 26/10/2026

- CI `40317113432` (`9c16238a`): lint corrigido; dois testes de manutenção ainda referenciavam serviços RAW/Gemma ausentes do inventário. Os testes agora exercitam o worker opcional de prévias, mantendo as garantias de não ativar serviço inativo e de ignorar serviço ausente. Os 29 testes de `scripts.test_python_security_release` passaram.
- Os builds AMD64/ARM64 revelaram ausência de `libexpat.so.1`; foi adicionada a dependência Debian `libexpat1`. O build local também demonstrou que `-v` retorna 255 na CLI 5.13. Conforme `rtgui/main-cli.cc` da tag upstream 5.13, a inicialização sem argumentos imprime a versão e retorna zero. Build e smoke agora exigem sucesso e banner de versão, sem ignorar falhas.
- Build AMD64 local com tag exclusiva `markina-retirement-ci:20261026-amd64` passou; imagem config `sha256:43ea629ff7009f9927340cb943cd508b2f7b3c80ada9e83816eff62e1824e03d`. Smoke em container temporário sem rede, somente leitura, sem dados reais, com 1 CPU/768 MiB passou nas três amostras sintéticas (0,926 s; 0,483 s; 0,430 s), preservando entrada, dimensões e RGB. Nenhum serviço compartilhado foi alterado. A decisão anterior de não construir localmente foi substituída por esta validação isolada.
- Lint de backend/testes/scripts alterados, OpenSpec estrito da change e `git diff --check` passaram; testes auxiliares de terceiros (11) e Pillow (2 + 13 + 14) passaram. `test_preview_adjustment.py`: 22 testes passaram na imagem Python 3.13, com testes/conftest/migrations montados somente para leitura e SQLite temporário. A tentativa no Python 3.12 do Windows teve 18 passes/4 erros de setup por ausência local de `mercadopago`; no container, a primeira montagem omitiu migrations (21 passes/1 erro), corrigida antes da execução final verde. As tasks 4.1/4.2 permanecem pendentes da evidência ARM64 e do CI completo no novo SHA.

- Antes de release, atualizar o inventário remoto de schema, ambiente, serviços/imagens ativos, filas/jobs RAW/Gemma, embeddings e volumes staging. A observação de 19/10 é histórica e o schema 0089 informado pelo proprietário não comprova estado de containers.
- Parada/recriação de workers, limpeza de imagens, exclusão de dados/volumes, migration ou deploy exigem plano de impacto zero e autorização operacional específica. Manter a change não arquivada até revisão humana e reconciliação do inventário de runtime.
- Após CI verde e revisão humana, sincronizar as specs principais e arquivar a change pelo fluxo OpenSpec.
