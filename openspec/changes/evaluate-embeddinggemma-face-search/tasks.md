## 1. Preparação

- [x] 1.1 Revisar e aceitar o protocolo, o escopo e os controles desta change antes de escrever harness ou integrar dependências. Evidência: pedido do proprietário de 11/10/2026 para iniciar a implementação do Gemma, após discutir benchmark real, motor global e modo shadow.
- [x] 1.2 Revisar configuração global e a regra de seleção solicitada pelo proprietário: um botão alterna SFace/Gemma; somente galerias criadas após a ativação Gemma podem usar o índice Gemma completo; galerias antigas ou com cobertura incompleta ficam integralmente em SFace.
- [ ] 1.3 Receber lote real escolhido para esta execução, verificar anotação/ground truth, origem, finalidade, autorização, categorias e plano de retenção/exclusão; não pesquisar fotos fora do lote.
- [x] 1.4 Confirmar proveniência, versão e licença dos candidatos elegíveis e registrar exclusões. Evidência: manifesto YuNet/SFace com SHA-256/MIT/Apache-2.0; README oficial Gemma na revisão 914f7f89142e33e77833254d9c9b90c3cef7303b declara Apache-2.0. ArcFace/InsightFace adicional excluído desta execução por falta de checkpoint com licença comercial demonstrada; nenhuma alegação de licença dos pesos não verificados. Ver validation.md e assessment-report.md.

## 2. Integração local Gemma e troca por galeria

- [x] 2.1 Implementar provider Gemma local para recorte facial alinhado, vetor 768d normalizado e remoção do crop temporário após processamento. Testes com runtime falso: `backend/tests/test_facial_gemma_provider.py`.
- [x] 2.2 Separar `model_id`, versão e dimensão; garantir que reindexação SFace não remova embeddings Gemma e que busca SFace continue consultando somente SFace/128d. Evidência: `backend/tests/test_facial_engine.py`.
- [x] 2.3 Criar migrações aditivas e endpoints globais com gates PlatformOwner + InstallationOperator; validar schema em SQLite e PostgreSQL e testar negação para outros administradores. SQLite e PostgreSQL passaram; 15 testes da suíte de migrations PostgreSQL preservam catálogo histórico, dados SFace, namespaces e recusam downgrade. Gates de cliente/administrador/proprietário sem operador, troca reversível e recusa em produção já validados. Ver validation.md.
- [ ] 2.4 Criar worker/imagem Docker experimental, provisionar pesos na revisão fixada, verificar marcador e confirmar suporte de instalação em amd64/arm64 com memória/CPU isoladas. Build ARM64 real executado em builder exclusivo; inferência revelou torchvision e chat_template.jinja ausentes, corrigidos com regressão. Nova inferência ARM está pendente; CI dedicado AMD64 será gate do deploy. Scripts operacionais agora gerenciam o lifecycle Gemma existente; não há ativação implícita pelo profile facial.
- [x] 2.5 Adicionar um único controle “Usar SFace/Usar Gemma” na página de configurações, com visibilidade apenas para proprietário e estado/prontidão agregados. Evidência: 3 testes do painel, `tsc`, ESLint sem erros e build Next.js concluído.
- [x] 2.6 Enfileirar Gemma somente para fotos de galerias criadas após `enabled_since`; falha Gemma não desfaz o job SFace e selecionar SFace pausa novos jobs sem apagar embeddings. Evidência: testes de indexação cobrem galeria antiga e nova.
- [x] 2.7 Roteamento por galeria: fixar engine no pedido, usar Gemma apenas com cobertura completa e atual de todos os ativos elegíveis, selecionar SFace integralmente em caso de pendência/falha/galeria antiga e suportar envio de referência e região clicada em ambos os engines. Evidências: seleção e fallback em `test_facial_search.py`, namespace 768d em `test_facial_engine.py`, rotas de região existentes e consulta completa Gemma em `test_gemma_query_worker_searches_the_pinned_768_dimension_namespace`.
- [x] 2.8 Executar validações locais aplicáveis e revisar diff. Evidência: lote direcionado final 29 passed mais o teste ponta a ponta do worker Gemma (1 passed); rodada ampliada 100 passed, um achado no inventário de limpeza foi corrigido e seu teste isolado passou; Ruff, `compileall`, `tsc`, testes/UI, ESLint sem erros, build Next.js, Compose config, Alembic head 0074 e `git diff --check` passaram. Não foram processadas imagens nem iniciados containers.

- [x] 2.9 Validar high-res com filas isoladas, retenção limitada ao TTL e falha Gemma sem mutação do lifecycle SFace; corrigir consulta por região no worker usando o engine fixado. Evidência: 5 regressões Gemma high-res, consulta 768d por upload/clique com troca global depois da criação, e negação de região em pasta não atribuída; validações finais em validation.md.
- [x] 2.10 Completar monitor Gemma: filas agregadas, dimensão fixa de worker/duração/erros, overlay e exportação sanitizada com testes. Evidência: testes do monitor/worker/filas e frontend; ausência de host permanece lacuna, sem alegar CPU/RAM por modelo.

## 2A. Entrega autorizada em homologação — 11/10/2026

- [x] 2.11 Integrar worker Gemma existente ao deploy, retomada e proteção de leitores da manutenção, sem ativação implícita nem alteração de ambiente; proteger pausa antes de Alembic e rollback por testes operacionais sintéticos. Evidência: regressão falhou antes da inclusão; test_gemma_operations.sh, test_deploy_homolog.sh, test_resume_homolog.sh, Ruff da política e git diff --check passaram em 11/10/2026. Descoberta por labels próprios, ausência sem start/build, parada/falha/leitor remanescente, healthcheck, retomada e rollback pré-Gemma cobertos.
- [x] 2.12 Validar migrations 0073/0074 em PostgreSQL isolado, sem dados operacionais, preservando o namespace SFace e recusando operações incompatíveis. Evidência: 4 testes focados passaram em 35,03 s; suíte PostgreSQL completa 15 passed em 171,59 s. Banco novo exclusivo em tmpfs, loopback 15470, memória 384 MiB/0,5 CPU. A comparação histórica de 0070 foi corrigida para excluir a coluna search_engine adicionada somente em 0074; nenhum schema de produto foi alterado para satisfazer esse teste.
- [x] 2.16 Provar em PostgreSQL que inferência Gemma não bloqueia SFace/prévias pela fonte compartilhada; proteger substituição/exclusão da fonte antes de persistir e limitar lease exclusivo Gemma a 900 segundos, preservando SFace e cleanup por lease. Evidência: regressão PostgreSQL falhou por lock_timeout antes da correção; cinco cenários concorrentes/mutação de fonte passaram em 48,50 s. Ver validation.md.
- [x] 2.13 Validar build/modelo real ARM64 com imagem e container exclusivos, memória/CPU limitadas e entrada sintética; medir consumo e registrar limites sem alegar eficácia facial. Evidência: smoke offline com pesos reais passou, 768d/norma 1/repetibilidade, 48,656 s frio/34,402 s quente e pico RSS 4.840,4 MiB sob 1 CPU/6 GiB; ver validation.md.
- [ ] 2.14 Revisar diff seletivo, validar CI, publicar PR para develop e fazer merge autorizado somente depois de inventário/plano atualizados e backup verificável.
- [ ] 2.15 Acompanhar deploy autorizado, confirmar schema/healthchecks/recursos vizinhos e iniciar explicitamente worker Gemma com SFace mantido; registrar evidência, sem ativar seleção Gemma ou processar lote real.

## 3. Harness e benchmark real

- [x] 3.1 Implementar harness separado do produto para comparadores e estratégias de recorte, sem persistência de vetores, fotos ou identidade no índice de produto. Evidência: scripts/embedding_engine_benchmark.py e 7 testes sintéticos; mesmos detector/caixas para SFace/aligned/context/whole_image, dimensões, calibração em validação, teste separado, RSS/CPU e carga de comparação em memória. Não mede fairness ou filas do produto. Dependência psutil em benchmark-requirements.txt, fora do runtime SFace.
- [ ] 3.2 Calibrar thresholds em validação e medir top-k, rejeição de desconhecidos, falsos positivos/negativos e margem com teste final separado.
- [ ] 3.3 Medir dimensões 768/512/256/128 do Gemma, custo de índice, latência por rosto, throughput, CPU, RAM e VRAM quando disponível.
- [ ] 3.4 Separar resultados por dificuldade somente nas categorias com amostras anotadas suficientes e registrar limitações.
- [ ] 3.5 Medir concorrência multi-fotógrafo/cliente, p50/p95/p99, filas, drenagem de lotes, pico de recursos e degradação sob rajada; declarar limites de fairness/isolamento não cobertos.
- [ ] 3.6 Excluir imagens, embeddings, rótulos pessoais e temporários; registrar evidência verificável da exclusão.

## 4. Relatório e decisão

- [ ] 4.1 Produzir relatório comparativo agregado, com protocolo, versões, licenças, hardware, métricas, thresholds recomendados e limitações.
- [ ] 4.2 Recomendar KEEP CURRENT ENGINE, REPLACE WITH EMBEDDINGGEMMA2, REPLACE WITH ARCFACE/INSIGHTFACE ou HYBRID ARCHITECTURE apenas se os dados sustentarem a decisão.
- [x] 4.3 Validar a change OpenSpec e revisar o diff sem sincronizar ou arquivar antes de revisão humana. Evidência: npx @fission-ai/openspec@1.10.0 validate evaluate-embeddinggemma-face-search --strict passou; git diff --check e revisão focada passaram. Change segue ativa, sem sync/archive.
- [x] 4.4 Manter a seleção Gemma limitada à homologação autorizada; nenhuma implementação local autoriza ativação em produção. Evidência: endpoint recusa prod/production; roteamento, enqueue e startup Gemma também bloqueiam produção. Teste verifica recusa antes de carregar assets. Consentimento/escopo/retensão existentes continuam obrigatórios; nenhum dado real ou servidor foi processado nesta execução.

## Bloqueios e limites

- O lote real, ground truth e manifesto de autorização desta execução não foram fornecidos. Métricas faciais reais e recomendação comparativa seguem pendentes; nenhum conteúdo da pasta operacional foi usado.
- O build real ARM64 foi executado em ambiente exclusivo; inferência corrigida e CI AMD64 estão pendentes. Ver validation.md para falhas reproduzidas/correções.
- O limiar Gemma ainda usa o valor operacional SFace e não está calibrado; o seletor continua restrito à homologação privada, sem recomendação de troca ou liberação para produção.
- A autenticação do proprietário não dispensa consentimento, elegibilidade, finalidade, retenção nem gates existentes em cada galeria. Não executar homologação, produção, deploy, alteração de segredo ou processamento de fotos reais sem a autorização operacional específica. Testes usam somente JPEGs/vetores sintéticos.
- A CLI OpenSpec foi executada transitoriamente via npx 1.10.0, sem alterar dependências do projeto; validação estrita passou.

## Continuidade — 11/10/2026

- Código local e harness validados; não confundir testes falsos/sintéticos com execução do modelo real. Ver validation.md.
- Pendências 1.3 e 3.2–3.6/4.1–4.2 exigem corpus autorizado/anotado e runtime real. 2.3 e 2.12 concluídas em PostgreSQL sintético novo. 2.4 exige validação real amd64/arm64; ARM usa recursos exclusivos limitados e AMD usará runner CI dedicado, preservando recursos vizinhos.
- Operação de publicação em homologação autorizada em 11/10/2026; inventário/plano em deployment-plan.md. Scripts corrigidos/testados incluem Gemma existente no lifecycle. Ainda não houve merge nem deploy nesta atualização; manter seleção SFace e não executar fotos reais.
