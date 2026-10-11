# Validação local — 11/10/2026

## Continuação autorizada depois da manutenção Docker

A limpeza/compactação foi autorizada separadamente e concluída fora dos repositórios: 12,35 GB de cache recuperável removidos por IDs, 48 registros compartilhados preservados, compactação restituiu 4,60 GB ao Windows; Docker reiniciado. O bloqueio anterior de daemon/disco local está superado, mas a RAM disponível local permanece inferior a 1 GiB; nenhum modelo pesado foi carregado no Windows. Inventário remoto e plano da publicação autorizada estão em deployment-plan.md.

Task 2.11: regressão operacional Gemma falhou antes da correção e passou após inclusão. test_gemma_operations.sh, test_deploy_homolog.sh (políticas de deploy/manutenção/produção/rollout incluídas), test_resume_homolog.sh, Ruff e git diff --check passaram. Fixtures de Docker falsas verificam labels exclusivos, ausência sem ativação, inclusão em build/start/pausa, falha de parada/leitor remanescente bloqueando Alembic, saúde Gemma, retomada de container existente e pausa antes de rollback para checkout sem Gemma. Nenhuma manutenção destrutiva foi executada.

## Escopo e resultados

- Suíte ampliada backend: **184 passed** em 373,49 s. Inclui concorrência existente de 100 consultas, engine, jobs, indexação, high-res, busca, regiões, monitor, observabilidade, capacidade, Gemma falso, migrations SQLite e harness. Um warning preexistente de ordenação de DROP de tabelas SQLite em fixture; não foi executada limpeza operacional.
- Após revisão das fronteiras e últimos guards: **77 passed** em 86,71 s nos arquivos test_facial_jobs, test_facial_runtime, test_facial_indexing, test_system_monitor, test_direct_region_search, test_embedding_engine_benchmark e test_facial_gemma_assets.
- Grupo high-res/regiões/provider/worker após as correções de autorização e crop temporário: **67 passed**, uma falha de fixture de posição de pasta; corrigida com position=1 e sua regressão passou na rodada final de 77. Nenhuma falha de produto permanece conhecida nessas rodadas.
- Frontend: **14 testes passed** (seletor e monitor), TypeScript sem erros, ESLint sem erros e build Next.js 16.3.2 concluído, 23 páginas estáticas.
- Ruff dos arquivos Python alterados, compileall, Compose base + overlays de prévias e monitor com config --quiet, git diff --check passaram.
- OpenSpec 1.10.0, validate evaluate-embeddinggemma-face-search --strict: **válido**. Cabeçalho delta corrigido para ADDED Requirements e tasks movidas para grupo correto. Não houve sync/archive.

## Achados corrigidos e contratos protegidos

1. Clique Gemma consultava região com default SFace no worker. Reproduzido com teste 768d por região que falhou antes da correção; upload/clique passaram depois. Engine fixado sobrevive a seleção global SFace posterior.
2. Falha/cancelamento/tentativas Gemma podiam sobrescrever estado ou métricas PhotoAnalysis SFace. Agora somente jobs index atualizam esse lifecycle/ajuste; testes preservam state=ready e métricas após falha Gemma.
3. Upload high-res não entrava na fila Gemma devido ao early-return do indexador legado. Finalização da fonte agora cria jobs independentes e idempotentes. Gemma não bloqueia geração de prévias; fonte espera job pendente somente dentro do TTL atual, sem renovação. Lease ativo protege qualquer leitor; expiração/desligamento libera fonte conforme contrato.
4. Roteamento exige cobertura integral da galeria, chave da geração atual, fingerprint high-res ou prévia limpa vigente, revisão/qualidade e heartbeat válido. Galeria antiga, pendência, geração antiga, preview regenerado ou heartbeat futuro/antigo preservam SFace.
5. Regiões de ambos os modelos exigem foto autorizada à cliente, inclusive pasta. Teste impede overlay/leitura de região em pasta restrita não atribuída.
6. Telemetria reconhece gemma/work.gemma em vocabulário fixo, sanitização, relatórios e frontend. Falha com retry não é contabilizada como sucesso. Filas Gemma entram em busca/indexação. Overlay inclui o novo worker; fonte CPU/RAM continua agregada por host, sem atribuição por engine.
7. Notificações de consultas Gemma usam o worker de busca existente e seu transporte configurado. Worker Gemma não disputa envio com configuração diferente.
8. Profile facial-gemma é independente do profile facial. Nenhum worker experimental inicia implicitamente pela ativação do grupo SFace. Startup, enqueue, seleção e API impedem Gemma em produção.
9. Build permite rede apenas no passo explícito de provisionamento fixado; runtime mantém flags offline. Marcador inválido/cache não verificado são rejeitados, sem substituir cache preexistente.
10. Alinhamento temporário é retornado somente quando pedido sem embedding SFace; não acrescenta crops aos resultados convencionais. Provider Gemma retira pixels temporários das observações retornadas.

## Harness isolado

Scripts/embedding_engine_benchmark.py usa somente manifesto explicitamente escolhido e arquivos listados dentro de seu diretório, sem varredura operacional, banco, API ou filas. Requer três partições gallery/validation/test e rejeita imagens idênticas entre partições. Para dados reais exige referência humana correspondente, origem/finalidade, expiração, atestado de workspace cifrado e plano de exclusão. Isso não substitui autorização externa real.

Reutiliza detecção/caixas para todos os comparadores: SFace alinhado e Gemma alinhado/contexto/imagem inteira. Trunca/renormaliza Gemma em 768/512/256/128. Calibra threshold/margem só em validação, mantém teste final separado, exporta somente agregados de identificação aberta e top-k. Vetores não são persistidos. Relatório deve ficar fora do diretório privado e não sobrescreve arquivo existente.

Coleta duração de embedding, CPU do processo/RSS e carga de comparação vetorial em memória com concorrência 1/2/4/8. Esses números não simulam sessões, fila durável, decriptação, throughput do modelo concorrente ou fairness multi-tenant; 3.5 continua pendente. Categorias reais e exclusão do corpus permanecem em 3.4/3.6, sob operação autorizada. VRAM não medida no protocolo CPU.

Dependências: face/gemma para modelos locais e benchmark-requirements.txt para psutil 7.2.2. Nesta execução somente psutil foi instalado em diretório externo de validação; nenhuma dependência pesada foi instalada no ambiente SFace e nenhum peso foi baixado. Os providers do teste são falsos; JPEGs do teste são sintéticos.

## Preflight estático do runtime

- PyPI confirma torch 2.14.1, sentence-transformers 6.1.0, transformers 5.19.0 e huggingface-hub 1.31.0 publicados e compatibilidade Python declarada >=3.10.
- Índice CPU oficial PyTorch contém wheels CPython 3.13 Linux x86_64/aarch64 para 2.14.1. Isso não comprova instalação/inferência no host alvo.
- README/config/modules oficiais Gemma na revisão 914f7f89142e33e77833254d9c9b90c3cef7303b confirmam arquitetura multimodal, 768d e Apache-2.0. Metadados da árvore declaram um safetensors de **1.488.915.288 bytes**; não foi baixado.
- Manifesto YuNet/SFace registra revisão, SHA-256 e licenças MIT/Apache-2.0. ArcFace/InsightFace adicional excluído por checkpoint comercial não comprovado.

## Bloqueios reais

Docker Desktop Linux não está disponível no pipe local. Disco local tem aproximadamente 3 GB livres; construir a imagem/pesos nesse estado pode afetar infraestrutura compartilhada. Não iniciar daemon, limpar recursos ou instalar runtime pesado para contornar. Build/load/inferência Gemma real e suporte ARM continuam sem evidência.

Sem instância PostgreSQL isolada disponível, migrations 0073/0074 foram verificadas apenas em SQLite e no head Alembic. Não aplicadas a banco operacional. Sem lote real, ground truth e autorização por execução, não há medidas de eficácia, calibração Gemma, concorrência real multi-fotógrafo ou recomendação de substituição. Limiar experimental ainda reutiliza configuração SFace.

Nenhum deploy, container operacional, alteração de .env/segredo, canal externo ou processamento de mídia real foi executado. Checkout principal e mudanças alheias preservados. Scripts operacionais existentes não gerenciam o lifecycle Gemma; provisioning/upgrade/cleanup do experimento exige inventário específico antes de qualquer execução autorizada.

## PostgreSQL e regressões locais — 11/10/2026

- PostgreSQL 17 em container novo exclusivo, tmpfs de 256 MiB, sem volume persistente, 384 MiB/0,5 CPU e loopback 15470. Nenhum banco operacional ou teste antigo reutilizado.
- Regressão histórica de 0070 reproduzida: catálogo ORM atual inclui search_engine, ausente nessa revisão. Corrigida somente a expectativa histórica; schema operacional preservado.
- Testes focados SQLite/PostgreSQL: 4 passed em 35,03 s. Suíte completa test_tenant_photographer_migration.py: 15 passed em 171,59 s.
- Cenário novo 0072→0074 preserva linhas legadas, embeddings SFace e busca antiga; insere vetores Gemma 768d separados, valida defaults, índice composto, novos tipos de job, restrição de engine e recusa de downgrade sem alteração de dados/head.
- Container sintético foi parado/removido depois dos testes; tmpfs descartado. Não houve exclusão de volume persistente.
- Lote backend atualizado (harness/assets/provider/runtime/search worker/indexing/high-res/monitor): 115 passed em 201,46 s, somente entradas sintéticas. Seis avisos preexistentes de lifespan FastAPI.
- Ruff backend/app e backend/tests passou; git diff --check passou. OpenSpec 1.14.0 --strict --all: 92 passed, 0 failed. Dependência psutil do harness adicionada somente à instalação de testes CI via benchmark-requirements.txt, preservando runtime SFace.
- Worker geral remoto foi retomado por resume-homolog.sh vigente depois de deadlock PostgreSQL preexistente; observado saudável cinco minutos depois. Nenhum código remoto foi corrigido fora do fluxo Git/CI.

## Runtime real, frontend completo e publicação — atualização 11/10/2026

- Build ARM64 real separado provisionou pesos fixados; primeira inferência encontrou torchvision ausente, comprovado no traceback. CPU torchvision 0.29.1 foi acrescentado exclusivamente ao Dockerfile.gemma; resolução real confirma torch 2.14.1+cpu compatível.
- Segunda inferência encontrou chat_template.jinja ausente. API oficial da revisão fixada confirmou o arquivo; allow_patterns agora inclui *.jinja e verificação de assets rejeita sua ausência. Duas expectativas falharam antes da correção; assets/provider/runtime depois: 16 passed em 19,98 s.
- Primeiro comando do smoke externo precisava PYTHONPATH=/app por estar montado em /tmp; corrigido somente no comando. Nenhuma falha teve OOM. Script reproduzível scripts/check_gemma_runtime.py não lê fotografia nem banco.
- Frontend completo inicialmente revelou respostas genéricas de branding entregues ao novo endpoint pelo mock; fronteira facial nos testes de branding agora responde 403, preservando contrato de administrador comum. A falha de timeout do monitor sob concorrência ampla não se repetiu com dois workers. 26 testes focados e depois 480 testes/60 arquivos passaram em 111,33 s. CI limita Vitest a dois workers. ESLint: zero erros, 37 avisos preexistentes; tsc passou.
- CI dedicado gemma-runtime construirá CPU AMD64 e executará o mesmo smoke offline antes do gate de deploy. Build limitado a 2 GiB/1 CPU; inferência 6 GiB/1 CPU. Inferência real ARM corrigida e resultado AMD64 ainda pendentes nesta atualização.
- Backup lógico online pré-merge exclusivo: /var/lib/markina-gallery/backups/pre-gemma-20261011T213949Z.dump; 21.795.803 bytes; modo 0600; pg_restore --list validou 1.107 linhas; SHA-256 3bbf117c5447e0937f609736eabab0776a49c5d1b3683b2fa9e165aaeac32807. Nenhum restore executado. Deploy produzirá seu próprio backup antes de Alembic.

## Inferência ARM64 e isolamento comprovados — 11/10/2026

- Imagem CPU ARM64 na revisão fixada, template Jinja incluído e torchvision 0.29.1+cpu. Smoke real com pixels pretos sintéticos 112×112, sem rede, banco ou mídias operacionais: exit 0, sem OOM, vetor finito 768d, norma 1,0 e repetibilidade conferidas.
- Oracle ARM64, limite 1 CPU/6 GiB, threads internas 1: primeira execução 48,656 s, seguinte 34,402 s, pico RSS 4.840,4 MiB. Esses números incluem somente o modelo e uma entrada sintética, sem detecção/qualidade/filas; não representam eficácia facial, throughput total nem recomendação de substituição.
- A medição motivou investigar fronteiras de lock. Cenário PostgreSQL com dois consumidores reais de banco reproduziu lock_timeout em PhotoAnalysis: Gemma segurava o lock usado por SFace/mídia. Gemma agora usa exclusivamente seu lease; não bloqueia PhotoAnalysis durante inferência. O engine relê fingerprint/expiração/pipeline e exclusão antes de persistir.
- Cinco cenários PostgreSQL passaram em 48,50 s: SFace conclui durante o cálculo Gemma e libera media_can_proceed; alteração de fingerprint, exclusão, expiração ou pipeline recusa resultado Gemma e preserva embedding SFace. Sem corpus real.
- Compose: lease exclusivo Gemma padrão 900 s, limite do contrato de configuração; SFace mantém 120 s. OMP/OpenBLAS/MKL limitados a uma thread somente em Gemma, coerente com limite CPU e smoke. Contratos Compose verificaram os valores separados.
- BuildKit e quatro containers sintéticos desta execução foram parados/removidos seletivamente após conclusão; nenhum recurso vizinho incluído. Imagem/cache exclusivos preservados para provisionamento. Arquivo de ambiente conferido pelo hash antes/depois, sem alterações.

## Checkpoint final de integração antes do PR

Suíte PostgreSQL completa após separação dos locks: 20 passed em 221,11 s. Inclui cinco cenários concorrentes/alteração de fonte, catálogo histórico e upgrade 0072→0074 com preservação. Container sintético novo parado/removido depois da validação; nenhum banco antigo ou operacional foi usado. test_deploy_homolog.sh voltou a passar após atualizar a expectativa do gate CI para incluir gemma-runtime, preservando todos os quatro gates anteriores. Ruff passou. Build Next.js passou novamente: 23 páginas estáticas, compilação 17,9 s e TypeScript 4,6 s. Frontend completo 480 passed já registrado.

Após a correção concorrente, lote engine/high-res/runtime/search worker/search/region/indexing/jobs/assets/provider: 111 passed em 310,97 s, seis avisos FastAPI preexistentes. Código funcional final é o desse checkpoint; mudanças posteriores serão de documentação/entrega ou exigirão repetir validação afetada.

## CI PR 158 — runtime AMD64 e achado no catálogo histórico

Push/PR publicados no SHA 854aa022f98d87b5fe6278a52ec16603e24b9db2. Run 38178350727: frontend, OpenSpec, gitleaks e gemma-runtime passaram. Smoke AMD64 real offline: 768d/norma 1/repetibilidade, 18,621 s frio/12,007 s quente, pico RSS 4.738,7 MiB sob 1 CPU/6 GiB. Continua sendo entrada sintética, sem eficácia facial demonstrada.

Backend CI: 1.345 passaram, 20 skipped, uma falha em test_limpeza_preserva_admin_conta_sessao_e_canal[postgresql]. O teste atual de inventário/limpeza montava explicitamente schema 0072, anterior à tabela Gemma classificada/preservada. O inventário recusou corretamente o catálogo incompleto; não enfraquecer essa proteção. A fixture operacional foi atualizada explicitamente para 0074 (head no helper histórico mapeia intencionalmente para fundação 0069), preservando os outros ensaios históricos. Teste também passa a comprovar que configuração Gemma, primeira ativação e autor são preservados pela limpeza sintética. Nenhuma limpeza operacional foi executada.

Imagem ARM64 preparada para a publicação do mesmo código funcional: sha256:0fc14ad1b41093ded5a23822f82201caef5cfbd0e611eac2243300a3893e579d, 3.185.234.779 bytes, tag exclusiva release-854aa022f98d. Builder exclusivo parado depois do build. Merge/deploy ainda não executados nesta atualização; backend corrigido deve passar novamente no CI.

Correção do teste operacional validada localmente em banco PostgreSQL sintético novo: test_tenant_migration.py completo, 7 passed/1 skipped em 99,40 s; skip é o cenário de limpeza SQLite, que exige PostgreSQL. Ruff e OpenSpec estrito passaram. Só teste/documentação mudaram após 854aa02; código funcional, dependências e evidências de runtime permanecem iguais. Novo CI completo é obrigatório antes do merge.
