# Evidências de validação — 25/10/2026

## Escopo e estado

Autorização direta: corrigir Pillow nos seis especializados antes do Mercado Pago. Worktree `feature/pillow-specialized-security`, PR258 do Dependabot reutilizado, main cef5bdf8 integrada sem reset/force push. Orders permanece no PR283/SHA53959492, CI40194974055 verde (1661 testes backend aprovados/23 skips), sem publicação.

**Nenhum serviço ativo foi substituído, parado ou reiniciado. Nenhuma migration, alteração de credencial, foto real, cobrança ou modificação de dados foi executada.** Nova consulta:15 serviços saudáveis, checkout1f4483bd, schema20261022_0087, HTTPS200 em healthz/api/health/raiz e nenhum marker pendente.

## Origem, licença e compatibilidade

Notas oficiais13.0.0 (16/10/2026): https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html . Python3.13 suportado; licença efetiva MIT-CMU, sem ativação/custo adicional. Avaliadas rupturas fromarray(mode), Image._show, get_child_images, MakerNote e PNG32bits: nenhum consumidor incompatível encontrado em app/spike; fromarray(uint8,RGB) não muda dtype. Nenhuma licença/revisão de modelo mudou.

Wheel oficial PyPI13.0.0 CPython313 ARM64 manylinux_2_27/2_28:6.515.908bytes, SHA256 `19b66ca0a4d25cc0200b381ce824c7ea090db61427315e73cfb05dbf1b35c369`. Manifesto: https://pypi.org/pypi/Pillow/13.0.0/json . Download HTTPS files.pythonhosted.org, tamanho/checksum conferidos, instalação offline sem resolver dependências.

O primeiro ensaio bloqueou diferenças de resize de retratos. Fonte oficial Resample.c13 confirmou mudança da ordem dos passes; os dois oráculos explícitos continuam bit a bit iguais entre versões e cada resize automático deve corresponder exatamente à regra respectiva. Sem tolerância geral. Na amostra RGB: máximo15/255, RMSE0,628; CMYK12/255, RMSE1,187; L2/255, RMSE0,477. Outros contratos iguais. Ver design; não alegar equivalência absoluta de qualquer fotografia.

## Seis candidatos nativos

Recibos0600 em pasta0700 no host: `pillow-prepare-20261025-01/prepared-v2.json`, provas individuais/logs e `signal-import-rehearsal.json`. IDs completos nos recibos; prefixos abaixo:

| Serviço | Anterior | Candidato | Pacotes comparados |
|---|---|---|---|
| face-index-worker |3f127a03e2c7|1b34cf3b2195|62|
| face-search-worker |5c783d14d971|ae32bc36c0d6|62|
| face-maintenance-worker |0bdc5fec1035|dd9a526e220a|62|
| face-gemma-index-worker |d353c1a5afc8|adca63778e0d|90|
| preview-adjustment-worker |4d17f0b3f06a|c7ded32123ee|60|
| raw-development-worker |8bb5cff14306|ec62cb836dad|60|

Pillow13.0.0 nos seis candidatos; Python3.13.16 e demais pacotes idênticos; pip check0 antes/depois. Fontes/manifests/migrations/modelos por hash, camadas anteriores preservadas e somente label adicional de rastreio. BuildKit precisou de alias local por conteúdo porque FROM com ID nu tenta resolução remota; nenhuma tag ativa sobrescrita. Sem apt, pull de base, Dockerfile normal, download de modelo ou inferência biométrica.

Matriz offline anterior/candidato: JPEG RGB/L/CMYK×EXIF1/3/6/8, orientação, dimensões, normalização RAW real sem EXIF, watermark/apresentação reais, referência BGR real onde NumPy está instalado, PNG RGBA/P/I;16 e thumbnails480/1600/2000 de padrão7MP. Limites1CPU/1GiB, sem rede, mounts, filas ou chaves de produção. Tempos/RSS nos recibos; ensaio curto não é benchmark de carga/calibração facial.

Imports dos seis entrypoints passaram. Containers descartáveis com imagens candidatas: wchan ocioso, suspensão de unless-stopped, SIGINT→130, retomada, restauração da política e limpeza SIGTERM→0; nenhum SIGKILL. Somente containers identificados do ensaio foram removidos. Consumidores reais mantiveram IDs/imagens/StartedAt. Lock ensaiado em pasta temporária: concorrência recusada e liberação posterior confirmada.

## Testes e limites

Barreira nginx ensaiada em container descartável da imagem exata, rede none, sem portas publicadas: health200/admin503, repetição preserva backup, restauração confere bytes originais inclusive quebras de linha. O primeiro harness tentou acessar upstream após restore, mas o resolver Docker dinâmico é propositalmente ausente nessa fixture: timeout não era falha de recuperação. O harness passou ao conferir arquivo restaurado/health, sem alterar o contrato503. Container encerrado por SIGQUIT0/removido; inventário completo dos15 ativos idêntico. Nenhuma configuração nginx ativa foi escrita.

Render Compose conferido em memória: env projetado/restart dos seis coincide com o atual, sem imprimir valores. O gate real recusou SHA fora de main antes de qualquer mutação. Provas privadas `projection-main-gate-proof.json` e `guard-rehearsal-proof.json`.

-2 testes de pin/consumidores,13 de candidato/origem/deriva/algoritmo/recibos e14 de orquestração sintética passaram. Cobrem aprovação/CI/inventário/filas, parada/saúde/digest, recuperação antes do snapshot e composição parcial, configuração/mounts preservados e recibo final idempotente após crash. Arquivos e diretórios de recibos/journal são sincronizados em disco; o resultado preserva o digest financeiro, sem valores de clientes.
-9 testes de contrato técnico de candidato passaram; dependência continua recusada para publicação API/web. Teste completo do workflow passou após commit0d694614: `publication_candidate_ready=false / arquivo_fora_do_escopo`. A falha anterior avaliava o HEAD antigo, ainda sem o manifest backend. Nenhum executor antigo foi ampliado.
-Ruff dos novos scripts e OpenSpec strict passaram. Sem limpeza de runtime elegível; apenas asserção da categoria de recusa técnica corrigida com regressão.
-Backend local com Pillow13: **83 aprovados/60 avisos em310,35s** (reference_store,media,RAWengines,preview_adjustment). Falhas iniciais do harness resolvidas por chave sintética explícita e SQLite em arquivo privado compartilhável pelo TestClient; nenhuma asserção ou código do produto mudou.19 testes faciais/provider Gemma adicionais passaram em venv existente com NumPy/Pillow12.3 (regressão de fonte, não prova de13); versão13 facial coberta nas imagens ARM64 e sujeita ao CI com face-requirements.

## Gates pendentes

Diff final/CI de PR e main/revisão humana do PR258. Ainda não há recibo selado/fingerprint operacional aprovado nem published.json. Runbook descreve aplicação/recuperação sem DDL. Depois da correção efetiva, renovar inventário/overlay/fingerprint Orders; não reutilizar o recibo antigo nem declarar Mercado Pago publicado. Nenhuma spec principal sincronizada/change arquivada sem revisão humana.

## Aprovação humana e acompanhamento da revisão final

O proprietário aprovou explicitamente no chat o PR258 e a publicação somente de Pillow13 nos seis processos, condicionados ao CI verde; manutenção já aceita. Head aprovado48fabf1705bfc909663a4b865661bf9163674c47, run40203301396. Não pedir novamente autorização para esse mesmo escopo após os gates; alteração material exige nova avaliação.

Gemma offline, frontend, gitleaks, OpenSpec e imagens AMD64/ARM64 aprovaram esta revisão. Backend integral ainda em execução. Runs anteriores40202193146/40202624262, substituídos pelos ajustes de durabilidade/restauração de bytes, foram cancelados para evitar duplicação; não constituem aprovação do head final.

Ensaio adicional do Compose real: seis imagens por ID sha256, em projeto temporário/rede none/sem mounts de produção, recriação somente depois de SIGINT130 e políticas suspensas, novos IDs/Pillow13/políticas restauradas, limpeza SIGTERM0. Health dos engines não foi exercido nesse stub; é prova do contrato Compose, não substitui imports/matriz/CI. Prova privada compose-identity-proof.json;15 serviços reais permaneceram idênticos. Nenhum serviço ativo ou migration alterado.

## Merge autorizado e inventário antes da janela

PR258 integrado por merge3d2ac6e7fb2e621e6ad468f9fd1233ffc909c7a3 após CI integral verde do head48fabf17/run40203301396:1597 aprovados/20 skips/620 avisos no pytest completo (1487,68s); concorrência PostgreSQL4 e exclusão1 adicionais aprovados. Gemma offline e demais jobs/gate agregado verdes. Nenhum job de deploy rodou. Autorização humana explícita condicionada a CI atendida para o PR; CI push de main40206489337 ainda pendente e obrigatório para seal/apply.

Inventário remoto atualizado após merge:15 saudáveis, mesmos seis IDs anteriores, schema0087, somente nginx127.0.0.1:8080;13 filas sem queued/pending/processing;68 notification_delivery unknown preservadas. Snapshot financeiro pré-janela salvo somente em arquivo privado0600, sem dados impressos. Ainda nenhum serviço ativo substituído/pausado. O baseline da aplicação permanece1f4483bd; main3d2ac6e7 identifica o coordenador revisado, não uma atualização API/web.

## Fonte de segurança após merge

Consulta autenticada/read-only ao GitHub após merge retornou9 alertas abertos:6vite,2@vitest/mocker e1undici; severidades2high/6medium/1low. Nenhum Pillow aberto (41 anteriores encerrados pelo manifest corrigido). Isso não prova runtime publicado: seis processos ainda aguardam a troca após CI main. Não atualizar essas outras dependências dentro da correção Pillow nem declarar ausência global de vulnerabilidades.

Conferência adicional: quatro scripts privados de preparação/operação correspondem byte a byte ao SHA main3d2ac6e7. A cópia inicial de prepare_emergency_api_image.py diferia somente em CRLF/LF do Windows; original preservado fora do checkout e cópia canônica corrigida na pasta privada. Nenhum código/configuração de serviço ativo foi alterado. O seal continua exigindo mainCI verde e igualdade dos helpers.

## Publicação efetiva e desvio operacional tratado

CI main40206489337/SHA3d2ac6e7 integralmente verde:1597 aprovados/20 skips/620 avisos,1134,04s; demais jobs/gate agregado aprovados. Classificação dependencies; todos os jobs de deploy automático ignorados. Recibo selado privado sealed-main.json, fingerprint cf1c0d5227f9218519acd741ffe596032dc38c932b90ddb79ec4469fa70ab3a9; inventário port/schema/imagens apresentado antes da operação autorizada.

Troca pontual dos seis concluída em25/10/2026 (containers novos iniciados15:45:48UTC/12:45:48São Paulo). Todos carregam Python3.13.16/Pillow13.0.0, imagens candidatas da tabela, restart unless-stopped/saudáveis. API/worker geral pausados e retomados nos mesmos IDs/imagens; nove serviços preservaram imagens/IDs/configuração e os sete não pausados preservaram StartedAt. Schema0087, digest financeiro idêntico antes/depois,15 saudáveis, HTTPS200/200/200, nenhum marker pendente. Nenhum DDL, restore de banco, credencial, modelo, dado financeiro ou foto real alterado.Todos os41 alertas Pillow foram encerrados no manifest;9 alertas nãoPillow permanecem fora do escopo.

A conferência pública imediatamente após nginx reload recebeu503 transitório e o executor rearmou corretamente a barreira, deixando journal e todas as imagens novas saudáveis. Não foi interpretado como sucesso. Sob o mesmo lock/recibo aprovado, reconferimos versões/config/schema/digest, repetimos somente a restauração já autorizada do arquivo nginx original e aguardamos propagação limitada15s. Observações reais [200,200,503]→[200,200,200], sem alterar binários/configuração original. published.json, public-health-reload-settling.json, post-release-inventory.json e post-release-runtime.json persistidos0600; journal removido somente após sucesso. Não foi necessário rollback ou SIGKILL. O helper versionado recebe regressão de polling limitado para futuras execuções; a cópia usada em produção permanece exatamente main3d2ac6e7, com o desvio manual explicitamente registrado.

Continuidade: Pillow publicado/validado, autorização atendida. Overlay persistente em pillow-prepare-20261025-01/active.compose.json consta dos labels Compose dos seis ativos; preservar junto com published.json e imagens anteriores. Retomar Orders com inventário novo, incluindo overlay e pin13; não reutilizar fingerprint antigo. Sync/archive da spec permanece para revisão humana final, sem alegar publicação do Mercado Pago nesta correção.
