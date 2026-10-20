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

## Validação e candidatos locais

A importação no Docker local usa manifest IDs diferentes dos config IDs do Docker clássico Oracle; o preparador exige hash criptográfico do config original e camadas exatas, sem aceitar simples semelhança de nome/tag. Uma transferência sem compressão foi interrompida por timeout SSH; o import incompleto não foi aceito como candidato e a retomada usou compressão de fluxo, sem arquivo ou escrita na Oracle.

CI inicial #39487877212 delimitou falha no teste real de adulteração do wrapper: o script app mudou de blob, mas o pin do wrapper versionado ainda era anterior. Corrigido somente APP_SCRIPT_BLOB_SHA para `e53a09dd453a7dd0353ce35ce42a56f6e2c3fc1e`, o blob Git exato revisado; a comparação e o teste negativo de adulteração permanecem intactos. A cópia instalada na Oracle **não** foi alterada. O primeiro job executou 35 testes de estado: 34 passaram e somente esse contrato de pin falhou. A nova execução completa deverá comprovar a correção; nenhum teste foi dispensado.

| Candidato ARM64 local | ID de manifest/index Docker local | Resultado |
|---|---|---|
| api | sha256:983a033145cc0e43a2c54855ce77a8c35770286fcb5610b21ec8b7fb59853936 | quatro pins e manifesto embutido corretos, pip check zero, 60 distribuições comparadas sem drift adicional |
| worker | sha256:f97071b7369f7e990cbb9fd2643ccde365b872a6c312214ca56e91301a55b4f2 | mesmas verificações independentes contra seu próprio ID anterior; não presumir identidade com API |
| face-index-worker | sha256:5e616cb2afa194dde81821a562f9af250d0a2e570708dfc6a47b41241e753034 | quatro pins corretos, pip check zero, 62 distribuições comparadas sem drift adicional; modelos verificados e provider inicializado |

Todos preservam Python 3.13.16 e a lista completa de camadas anteriores; acrescentam somente instalação dos quatro wheels sem dependências e cópia do requirements-push aprovado. Versões observadas: aiohttp 3.14.4, multidict 6.9.1, urllib3 2.8.0, yarl 1.25.1. São imagens **locais**, não publicadas em registry e não carregadas/implantadas na Oracle. IDs de Docker clássico/config e de manifest/index são explicitamente distintos. O inventário completo e os IDs estão em candidates-final.json e installed-baselines.json no diretório de evidências.

Cinco consumidores permanecem sem candidato próprio por capacidade local, sem tentativa de contornar a reserva de 2 GiB ou limpar Docker:

| Consumidor | Livre / mínimo conservador para importação |
|---|---|
| face-search-worker | 2,94 / 3,01 GiB |
| face-maintenance-worker | 2,94 / 3,01 GiB |
| preview-adjustment-worker | 2,94 / 3,18 GiB |
| raw-development-worker | 2,94 / 3,51 GiB |
| face-gemma-index-worker | 2,94 / 7,93 GiB |

A igualdade das camadas SFace não foi usada como prova de equivalência integral de configuração entre IDs nem como licença para substituir os outros dois candidatos. A homologação ARM64 desses cinco consumidores **não foi executada/concluída**. O CI Gemma sintético em AMD64 não substitui esse requisito.

### Testes executados

- 29 testes novos de política, comparação completa de pacotes, identidade importada, daemon exclusivamente local, dispatch shell e oito cenários simulados: passaram. Incluem recusa de tarefa ativa/ausência de ack/barreira e rollback inverso preservando dados legítimos criados durante o rollout.
- Regressão local legada de estado: 35 testes executados, 34 passaram e um skip documentado de flock real Windows; wrapper adulterado é recusado. Política web/shell passou. Linux CI mantém flock real obrigatório.
- Regressões existentes de dependências: 19 passaram; classificação: 13; escopo app: 11. Ruff e OpenSpec strict passaram.
- API ARM64: 40 contratos sintéticos (Web Push/SSRF, jobs/leases faciais, runtime facial e interface RAW) passaram. A primeira tentativa teve 11 falhas 403 por montagem incompleta do harness, que omitia backend/conftest.py e seu seed sintético de tenant. Montagem corrigida com a fixture oficial e pyproject, sem alterar testes ou gates; repetição completa: 40 passed.
- SFace ARM64: integridade dos assets existentes verificada, provider OpenCV carregado, entrada preta sintética sem faces e dimensão contratual 128 preservada. Mais 34 testes de provider, modelos/schema, entrypoint, runtime e jobs passaram; nenhuma fotografia real, embedding de cliente ou reindexação.
- Startup API ARM64: TestClient/ASGI health 200 e admin sem sessão 403 passaram com SQLite exclusivamente tmpfs e chave de capacidades **sintética dedicada**. Entrypoints dos workers importaram sem iniciar loops. O harness inicialmente sombreava o objeto ASGI com o pacote app; depois faltou a chave sintética exigida pelo gate. Ambos os erros do harness foram corrigidos, sem alterar código da aplicação nem retirar validação de configuração. O programa anterior também exercitou aiohttp/yarl/multidict e urllib3 apenas contra HTTP sintético em loopback, sem conexão externa.
- Não foram exercitados providers reais de mensagens/pagamento, fluxos autenticados com clientes, inferência com fotografias reais, Gemma ARM64 ou binários RAW/prévias nesses candidatos ausentes. Import de worker não é startup operacional completo nem drain.

### Revisão e integração

[PR #257](https://github.com/conradodeita/markina-gallery/pull/257) contém somente infraestrutura/preparação, testes e documentação. A revisão manual do diff preservou o fluxo legado, os helpers pinados e a comparação criptográfica do wrapper; não há migração, atualização de requisito, Dockerfile oficial, Compose, modelo ou loop de worker. O conector Code Review respondeu “Connect your GitHub account to continue”; revisão externa por esse conector **não verificada**. As proteções consultadas exigem os seis checks, strict e enforce_admins; zero aprovações humanas obrigatórias.

Classificação executada contra a baseline de produção: release_scope=dependencies. Deploy homolog aceita somente push develop; preflights/releases de produção exigem app ou facial; rollback exige workflow_dispatch explícito. Esta change não adiciona operação de publicação. A integração e o CI do SHA definitivo são acompanhados na PR #257; não dispensar checks/revisões obrigatórios para integrar as evidências.

Wrapper instalado foi consultado apenas por metadados e pin: root-owned 0755, APP_SCRIPT_BLOB_SHA `6767d0ba092adb23666ab612db505af2e0900b35`, diferente inclusive do pin anterior do repositório. Nenhuma instalação, edição, sudo ou acesso a authorized_keys foi feito. O canal restrito atual não está reconciliado com o executor revisado; futura mudança desse controle exige autorização operacional própria, após resolver o executor/drenagem, não um bypass.

## Decisão funcional

**NO-GO — BLOQUEADO.** Cinco candidatos/homologações ARM64 faltam por capacidade, os processos antigos não oferecem barreira/drain cooperativo, e o executor operacional/recuperação Python ainda não estão implementados. A simulação não preenche essa lacuna. O wrapper restrito instalado também conserva pin antigo. Não há fingerprint operacional Python ou prompt seguro de publicação coordenada nesta missão. A integração da preparação no GitHub não corrige as bibliotecas efetivamente executadas na Oracle.

Refatoração proporcional: preservar executores e contratos legados; apenas adicionar dispatch Python antes do parser antigo e módulo isolado. Não alterar helpers pinados, wrapper remoto, allowlist app/facial, Dockerfiles, Compose, pacotes ou modelos. Não há remoção segura de código legado nesta tarefa.
