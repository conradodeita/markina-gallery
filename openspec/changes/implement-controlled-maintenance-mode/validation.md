# Validação — 20/10/2026

## Implementação

- O controle usa chaves Redis próprias e operações Lua atômicas para iniciar/finalizar manutenção e registrar/confirmar operações ativas.
- `CONTROLLED_MAINTENANCE_ENABLED` é opt-in; ausente ou `false` não acessa Redis e preserva o fluxo normal. Compose base injeta a flag em API, worker geral e quatro workers faciais; overlays entregam-na a preview adjustment e RAW.
- A middleware ASGI fecha ingressos comuns com HTTP 503, mantendo `/health` e `/healthz`; os callbacks exatos `POST /internal/whatsapp/webhook` e `GET /infinitepay/return` permanecem registrados durante a manutenção. Qualquer HTTP 5xx, exceção ou falha de ACK deixa o recibo persistente.
- CLI `maintenance-begin`, `status`, `wait`, `verify-state` e `maintenance-finish` fecha o fluxo explícito. Retomada exige identidade ativa correta, ausência de marcadores Redis e ausência dos estados persistentes de trabalho `processing`/`receiving` verificados pelo CLI.
- A inspeção dos consumidores no Compose confirmou cobertura dos oito runtimes Python conhecidos. Os wrappers cooperativos existentes nos workers permanecem dentro dos mesmos arquivos locais; nenhuma fila é apagada ou migrada.

## Evidência executada

- A suíte final, configurada como o CI (`DATABASE_URL` padrão ausente, `PYPPIC_TEST_DATABASE_URL` no PostgreSQL 16 descartável e `PYPPIC_TEST_REDIS_URL` no Redis 7 descartável), passou: **29 passed, 8 warnings**.
- Os seis avisos de lifecycle são `DeprecationWarning` de `FastAPI.on_event` em handlers de startup/shutdown preexistentes em `backend/app/main.py` e na integração TestClient. Não apontam para a middleware nova nem para falha de lifecycle introduzida pela change.
- Os outros dois avisos SQLAlchemy são `SAWarning` de `Base.metadata.drop_all` em fixtures existentes (`test_unified_checkout.py:62` e `test_whatsapp_delivery.py:67`), por ciclo de FK sem ordenação resolvível. Não alterados: o teardown pertence a fixtures fora da change e não afeta os resultados; corrigir fixtures gerais ampliaria o escopo.
- A suíte foi executada com containers descartáveis PostgreSQL `16-alpine` e Redis `7-alpine`, sem bind mounts, somente em portas loopback. Testes adicionais verificaram conexão PostgreSQL, callback sintético com commit antes do ACK, upload ASGI admitido antes do gate, job `queued` preservado, bloqueio de novo ciclo, falha sem ACK e retomada. Nenhum pagamento, serviço externo ou dado de cliente foi usado.
- A preparação inicial usou porta/nome fora da allowlist do fixture de checkout e foi corretamente rejeitada antes da execução desse teste. O teste PostgreSQL foi repetido em `127.0.0.1:15470/pyp_photographer_test`; os containers PostgreSQL/Redis descartáveis foram removidos ao final. Nenhum volume nomeado foi usado.
- `ruff check` nos arquivos Python afetados: aprovado. `python -m compileall` nos módulos Redis/CLI: aprovado.
- Docker Compose `config --format json` com todos os perfis, `.env.example` e overlays base, preview e RAW: válido; os oito consumidores (`api`, `worker`, quatro workers faciais, preview e RAW) reportam `CONTROLLED_MAINTENANCE_ENABLED=false` por padrão.
- O job backend do CI provisiona Redis 7 descartável e passa URLs específicas dos serviços PostgreSQL/Redis aos testes de integração, então os testes reais não são pulados. Em `pull_request`, os jobs de deploy de homologação/produção têm condições falsas; publicação permanece vinculada a push/dispatch na `main` e aos gates existentes.
- `openspec validate implement-controlled-maintenance-mode --strict`, `ruff check`, `compileall` e `git diff --check`: aprovados nesta branch isolada.
- Regressões dos handlers financeiros e WhatsApp passaram. Nenhum provedor real foi chamado.

## Bloqueios e limites

- A primeira ativação continua **NO-GO**: os processos atualmente publicados não reconhecem a flag nem o gate; não existe pausa/ACK legado comprovado que possa ser instalado retroativamente. Não houve tentativa de usar Redis para alegar controle dos processos antigos.
- Os testes não comprovam retry/reconciliação de InfinitePay nem da origem do webhook WhatsApp durante uma parada/substituição da API. Um release que interrompa a API permanece bloqueado até garantia por provedor ou receiver durável validado.
- PR #260 não foi consultado, alterado ou integrado. Nenhuma alteração operacional, deploy, restart, migration, operação de banco/Redis real ou contato com Oracle ocorreu.
- A implementação fica **desativada por padrão** em `.env.example` e nos oito consumidores Compose. Habilitá-la exige configuração explícita em todos os processos.
- Este modo não resolve retroativamente o bootstrap dos processos legados: processos já publicados não consultam a flag/gate e não há pausa/ACK legado comprovado para a primeira substituição.
- A continuidade/retry/reconciliação dos callbacks durante parada ou substituição da API continua sem comprovação; callbacks monitorados só podem ser aceitos enquanto a API instrumentada está em execução. Não usar esta implementação como autorização de release.
- O código foi isolado em branch/worktree próprios e não contém o executor experimental de release Python. O PR draft e a revisão humana permanecem pendentes; PR #260 segue fora do escopo.
