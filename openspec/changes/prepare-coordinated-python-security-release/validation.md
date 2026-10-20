# Evidência de preparação Python

## Inventário somente leitura

Main inicial: `27e1b8ffa0917b4dc2120bd4a26e09c6cae47e0f`. Oracle consultada em 20/10/2026 às 19:34 UTC: checkout limpo nesse SHA, 15 serviços saudáveis, ARM64, Python 3.13.16 em todos os consumidores. Face-index continua com seis reinícios, sem incremento desde o web-only. Não há evidência nova que justifique investigação paralela dos reinícios.

Evidências sanitizadas fora do Git: `C:/codex-data/release-evidence/python-release-preparation-20261020/` (`oracle-inventory.json`, `installed-baselines.json`, `queue-aggregates.json`, logs de candidatos). Não foram consultados payloads, fotografias, embeddings, mapas de ambiente, credenciais ou conteúdo de backups. O inventário de distribuições usa somente importlib.metadata. Exportações Docker por IDs transportam imagens, nunca containers, volumes ou configurações do host.

| Consumidor ativo | ID anterior (sha256) | Dockerfile / composição | Obrigatoriedade |
|---|---|---|---|
| api | afc54e0ff0b008ac7bcc2ab28095f279da6213aaa5bec1ac98fae8269fc0715c | backend/Dockerfile | obrigatório |
| worker | 25067618cf99f3b662f9096fc2f7aa88bcf272da5b2ea62dd91d9de9bd8d3b21 | backend/Dockerfile | obrigatório, imagem distinta da API |
| face-index-worker | 3f127a03e2c7336c62532ad1febdca1de38bf2c40373bb6081b24ca884a5f388 | Dockerfile.face + requisitos faciais | opcional já ativo |
| face-search-worker | 5c783d14d9714a89dc4ecde53878c81b5bc82f87788d5cdafad6a9d5475847c2 | Dockerfile.face | opcional já ativo |
| face-maintenance-worker | 0bdc5fec10352c85cbfd6e8e6dba6fe7065f36d47c5e39fbc6a6be0334443381 | Dockerfile.face | opcional já ativo |
| face-gemma-index-worker | d353c1a5afc82a39c741ef034fb58c10af4cc3d38dff4340da4a63c00163f597 | Dockerfile.gemma + face + torch/Gemma | experimental já ativo; saúde não comprova inferência |
| preview-adjustment-worker | 4d17f0b3f06a904a6b985ae018322cf28b114c64bc9711467b5b18020e24ce60 | Dockerfile.preview-adjustment + RawTherapee | opcional já ativo |
| raw-development-worker | 8bb5cff143069e15e1426ae7f60cc0a564c1b9320ee0d4b69fbdb054bb368449 | Dockerfile.raw-development + LightCraft/RawTherapee | opcional já ativo |

Todos os oito têm aiohttp 3.14.3, multidict 6.8.0, urllib3 2.7.0 e yarl 1.24.5; todos precisam da correção quando sua publicação for segura. Não presumir imagem compartilhada: apenas as três imagens SFace têm as mesmas camadas RootFS; IDs e serviços são distintos. Todas incluem requirements.txt → requirements-push.txt. Nenhum RepoDigest de registry nas imagens próprias observadas.

Web atual `sha256:768698a20b7042cf63a6e56df74fdea18a8e86b7086bbaa6c5bb8ba79d59250d`, Next 16.4.2 e React/DOM 19.3.1: fora do escopo. API ainda declara source `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`; diff Git desse source para main é vazio em app, modelos e Dockerfiles, mantendo somente os manifests de dependências pendentes.

Capacidade observada: 4 CPUs, aproximadamente 18,6 GiB de RAM e 62,5 GiB de disco disponíveis. Sem lock de release ou marcadores pendentes. Imagens anteriores presentes e recibos web válidos; backups existentes consultados apenas por metadados, sem restaurar/validar conteúdo.

Agregados às 19:45 UTC: facial 3 queued, 2 failed, 3625 completed, 93 cancelled; mídia 3366 completed; ajuste 3359 ready; RAW e e-mail vazios; WhatsApp 15 accepted, 183 expired e 1 failed. Nenhum estado processing nesses agregados. Falhas registradas não provam falha recente: o recorte anterior mostrou zero atualizações failed nos últimos 15 minutos. Não consumir ou reclassificar qualquer job.

## Contrato operacional e bloqueio comprovado

`facial/jobs.py` claim usa SQL SKIP LOCKED, token, attempts e lease com commit antes do processamento; complete/fail atualizam SQL. `facial/runtime.py` usa BRPOP somente como wakeup e volta ao SQL. `face_worker.py` faz reconciliação ao iniciar index e preserva a restrição de Gemma fora de production. Nenhuma dessas garantias equivale a um drain cooperativo reconhecido antes de SIGTERM.

`worker.py::run_cycle` inclui providers externos, outboxes e lifecycle além de mídia. `preview_adjustment/worker.py` e `raw_development/worker.py` não têm barreira de admission/drain. RAW persiste processing antes de renderizar e recupera após 20 minutos com limite de tentativas. Interrupção pode consumir tentativas ou tornar efeitos externos ambíguos. Não alterar esses loops fora da autorização restrita a scripts/testes, nem prometer ausência de duplicação com um stop baseado em contagem zero.

Assim, o escopo Python no executor oficial permite preparação e simulação, mas recusa modos operacionais. A simulação modela um contrato de barreira/ack que os processos reais **ainda não implementam**. A ausência de um executor operacional completo de workers permanece task 3.3 aberta e impede GO. Não existe fingerprint operacional Python nem publicação autorizada nesta missão.

## Validação em andamento

Resultados finais de candidatos, testes, revisão e CI serão registrados antes da conclusão. A importação no Docker local usa manifest IDs diferentes dos config IDs do Docker clássico Oracle; o preparador exige hash criptográfico do config original e camadas exatas, sem aceitar simples semelhança de nome/tag. Uma transferência sem compressão foi interrompida por timeout SSH; o import incompleto não foi aceito como candidato e a retomada usa compressão de fluxo, sem arquivo ou escrita na Oracle.

CI inicial #39487877212 delimitou falha no teste real de adulteração do wrapper: o script app mudou de blob, mas o pin do wrapper versionado ainda era anterior. Corrigido somente APP_SCRIPT_BLOB_SHA para `e53a09dd453a7dd0353ce35ce42a56f6e2c3fc1e`, o blob Git exato revisado; a comparação e o teste negativo de adulteração permanecem intactos. A cópia instalada na Oracle **não** foi alterada. O primeiro job executou 35 testes de estado: 34 passaram e somente esse contrato de pin falhou. A nova execução completa deverá comprovar a correção; nenhum teste foi dispensado.

Refatoração proporcional: preservar executores e contratos legados; apenas adicionar dispatch Python antes do parser antigo e módulo isolado. Não alterar helpers pinados, wrapper remoto, allowlist app/facial, Dockerfiles, Compose, pacotes ou modelos. Não há remoção segura de código legado nesta tarefa.
