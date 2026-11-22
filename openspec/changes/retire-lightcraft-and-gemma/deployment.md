# Release de aposentadoria LightCraft/Gemma

## Autorização e limites

O proprietário autorizou em 26/10/2026 corrigir até merge e deploy bem-sucedido. CI verde, inventário atual, preparação das candidatas, preservação de dados e procedimento de recuperação são gates obrigatórios. Não há autorização para excluir histórico, tabelas, imagens ou volumes.

## Inventário inicial somente leitura — 26/10/2026

- Host `ubuntu@132.145.193.169` (`clearbudget-vnic`), projeto `markina-gallery`, raiz `/opt/markina-gallery`, checkout limpo em `f9091a7be60314285e2c19b762c62eb5b64183e5`.
- Entrada exclusiva Markina `127.0.0.1:8080`, domínio `https://markina.pickyourpic.com.br`. O runtime declara `APP_ENV=staging`; preservar esse valor e demais controles sem inferir equivalência com nome de GitHub Environment.
- Schema observado via transação somente leitura: `20261025_0089`. Nenhuma migration é necessária.
- API/worker: `sha256:f1715fb18dacbcf24e23bef75546729c9aeebc8ac2ade7c40c0f8aa5bb41ec49`; web: `sha256:4538c63e6beba1bcc7b926ccbcd27685b7ac05d47a524d8831c8a2e3be91b606`.
- SFace index/search/maintenance, preview adjustment, RAW e Gemma estão ativos e saudáveis. Banco, Redis, Nginx e Evolution também saudáveis. Imagens especializadas e overlays serão fixados na evidência de preparação imediatamente anterior ao rollout.
- RAW: nenhum job; uma configuração histórica habilitada em RawTherapee. Gemma: configuração desabilitada, 126 jobs cancelados e 86 concluídos; nenhum job facial pendente/processando. Prévia: 3.593 resultados `ready`. Estas são contagens históricas, não autorização para apagá-las.
- Configuração ativa tem overlays de branding, monitor, manutenção Pillow e duas publicações Orders; há override RAW ainda ativo. Os overlays e patches de segurança não podem ser perdidos na troca. Segredos não são impressos nem copiados ao Git.

## Plano de impacto zero aplicado — 26/10/2026

1. Inventário imediatamente anterior validou SHA implantado `f9091a7be60314285e2c19b762c62eb5b64183e5`, schema `20261025_0089`, capacidade, configuração Compose completa, hashes de arquivos de segredo sem revelar valores, serviços saudáveis, filas sem trabalho ativo e dados históricos/financeiros. A configuração e imagens anteriores foram preservadas no diretório privado de operação do projeto.
2. As imagens candidatas foram construídas sem substituir containers. Conferimos igualdade das versões e pacotes Python, `pip check`, ausência dos módulos RAW/Gemma, integridade dos modelos SFace, versões Node/Next/React e RawTherapee 5.13. Os rehearsals isolados de startup, parada, manutenção Nginx e callback não enviaram mensagens reais.
3. A PR [#292](https://github.com/conradodeita/markina-gallery/pull/292) foi mesclada sem bypass no commit `c1944189761799be96eeeb921cad9906484d8b09`. O CI da PR passou no SHA `0f8015157488085338d63322fc4fc8f450b64f2a` (run `40334382185`); o CI do SHA de merge na `main` passou integralmente (run `40338625688`), incluindo backend, frontend, OpenSpec, Gitleaks, políticas, imagens AMD64/ARM64 e o contexto de compatibilidade legado.
4. O executor especializado usou lock de release do projeto, barreira de manutenção testada e desligamento gracioso após confirmar filas ociosas. Durante o corte, rotas de cliente ficaram temporariamente em manutenção 503, mantendo os health checks disponíveis. Recriou apenas API, web, worker geral, workers SFace, manutenção facial e ajuste de prévias. Os workers RAW e Gemma terminaram com saída controlada 130 e política de reinício `no`; containers e imagens anteriores foram preservados para recuperação. Nenhum container de banco, Redis, Evolution ou Nginx foi recriado, e nenhuma porta, rede, volume ou arquivo `.env` foi alterado.
5. O executor confirmou schema 0089 e igualdade dos fingerprints de dados financeiros e históricos antes de retomar escritores; não executou migration, DDL, purge ou exclusão de dados/imagens/volumes. O dump de recuperação `pre-retirement.custom` está retido com modo 0600 no diretório operacional privado, fora do Git.

### Resultado do runtime

- Commit ativo: `c1944189761799be96eeeb921cad9906484d8b09`; `APP_VERSION` da API corresponde a esse SHA; ambiente preservado como `staging`.
- Imagens candidatas ativas (digests verificados após o rollout): API/worker `sha256:06e3c1127212fab1629157f7e9c90f801d88e8a949b67795c8d22186a105e815`; web `sha256:1edb7f5d74323162b0ecb93c55fc725050d36fe9f9f06e57504df4ac23e2b6e4`; SFace index `sha256:fc2cb47fa432f880dfe380cb6f6efd8b91e241379d280f06a13d8e8b5739c0a4`; SFace search `sha256:a0c1aa1ba4b19e8b3f6cd1198ff6ca78feab0dde14c5e10bc15490066975cd92`; manutenção facial `sha256:a02de031663488c6a238a745e1cd86a15292812723f22c86a26edab645d6eccc`; ajuste de prévias `sha256:48fa9dc8a2c94d5398a502ad02fcbcab89a660039c66d08470c0ae82e81ce44e`.
- Todos os serviços Markina preservados estavam saudáveis; workers aposentados permaneceram parados. `/`, `/healthz` e `/api/health` no domínio HTTPS responderam 200. `/api/admin/facial-engine-experiment` respondeu 404. A CLI ativa do worker de prévias informou `RawTherapee, version 5.13, command line.`; filas continuam sem tarefas `queued`, `pending` ou `processing`.
- A identidade operacional, recibo, configuração anterior e nova estão em `/var/lib/markina-gallery/deploy-state/retire-prepare-20261026-09d5dfd4/` com permissões restritas. A identidade registra conclusão para o SHA `c1944189…`, schema 0089, fingerprints de preservação e os digests acima. O retorno do executor foi `release=passed`, `protected_services_unchanged=true`, `data_preserved=true`, `retired_workers_stopped=true`.

O procedimento API/web genérico permanece bloqueado para esta mudança especializada: seu manifesto antigo espera schema 0087 e não inclui workers. Não flexibilizar essa classificação nem executar o release Orders pontual de outra revisão. A única referência `gemma-runtime` remanescente no workflow é um contexto transitório exigido pela proteção externa da `main`; ele apenas espelha o sucesso do agregador atual, sem construir ou executar Gemma.
