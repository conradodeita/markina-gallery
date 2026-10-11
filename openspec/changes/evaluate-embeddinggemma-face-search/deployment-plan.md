# Publicação experimental em homologação — 11/10/2026

## Authorization

O proprietário solicitou nesta conversa: “Continue com o Gemma, em seguida faça push, merge e deploy”. Esta autorização cobre a publicação isolada em homologação pelo fluxo vigente e a preparação necessária do runtime; não autoriza produção, mudança de secrets/.env, exclusão de dados, reindexação do acervo ou uso de fotos reais em benchmark. O seletor global continuará em SFace na entrega; a seleção experimental cabe ao proprietário depois da prontidão.

## Inventory

Inventário SSH somente-leitura: Oracle `132.145.193.169`, ARM64, `/opt/markina-gallery`, checkout limpo no SHA `63a6c78a511431f160319dedab24d573f1e204de`, mesmo origin/develop da base local. Alembic `20261009_0072 (head)`. Memória total 23.988 MiB, disponível 19.911 MiB; disco disponível 111.897.968.640 bytes. Esta medição deve ser atualizada antes do merge/deploy.

- Entrada existente `https://markina-homolog.duckdns.org`, Nginx próprio em `127.0.0.1:8080 → 80`, healthz local e público aprovados.
- API, web, Nginx, três workers SFace, ajuste de prévias, PostgreSQL/Redis e Evolution saudáveis. Worker geral parado, saída 1, sem OOM, desde `2026-10-11T19:47:22Z`; traceback sanitizado indica `sqlalchemy.exc.InternalError` em worker/media. Condição anterior a esta entrega; deve ser delimitada e retomada por procedimento vigente antes do gate de deploy.
- Firefly bot/API/frontend/banco ativos; Proxy Manager e Portainer ativos. Não serão alterados, reiniciados ou incluídos em qualquer comando Compose desta entrega.
- Volumes próprios persistentes preservados: pgdata, redisdata, media-source, media-derivatives, media-history, facial-references, branding-assets e os três Evolution. Nenhum volume será excluído.
- Secrets exigidos existentes e origem pública correta, confirmados somente por presença/igualdade booleana. APP_ENV existente é staging; FACIAL_PROCESSING_ENABLED=true. Não é necessário editar ambiente.
- CI atual de develop verde, run `38150712437`. Nenhum merge novo executado neste inventário.

## Plan

1. Validar scripts com fronteiras Docker falsas, regressões locais e migrations em PostgreSQL sintético exclusivo; não reutilizar os dois bancos de testes antigos nem dados operacionais.
2. Preparar contexto mínimo de build sem `.env`, credenciais, bancos, fotografias ou diretórios de teste. Validar imagem ARM64 em diretório `/tmp/pyp-gemma-runtime-20261011-914f7f89142e` e builder exclusivo `pyp-gemma-validation-20261011`; build com teto de 2 GiB e 1 CPU. Não alterar builder default, kernel/binfmt ou configurações Docker globais.
3. Provisionar publicamente somente a revisão Gemma `914f7f89142e33e77833254d9c9b90c3cef7303b`, YuNet/SFace verificados e dependências CPU fixadas. Validar load/embedding de imagem sintética em container sem banco/rede/mídia operacional, teto de 6 GiB e 1 CPU. Compatibilidade efetiva AMD64 permanece pendente até validação específica, sem inferir sucesso a partir de metadados.
4. Commit/push seletivos e PR para develop; aguardar todos os gates CI e revisar diff. Não incorporar alterações alheias do checkout principal. Não usar trailers Homolog-Cleanup.
5. Antes do merge que dispara deploy, atualizar inventário e criar/verificar dump lógico exclusivo com bytes/SHA-256/TOC e permissão restrita. Seguir CI/Environment homolog, sem hot patch ou contorno de gates. A janela interrompe somente API/workers Markina antes de Alembic; vizinhos, proxy, Evolution, PostgreSQL/Redis e seus volumes permanecem preservados.
6. Aplicar somente migrations aditivas `0072 → 0073 → 0074`, confirmar head e saúde. Elas preservam ambos os namespaces e adicionam setting, tipos de job, índice composto e engine fixado nas consultas antigas como SFace. Não haverá downgrade/restauração automática; schema alterado bloqueia rollback automático incompatível. Backup antes da pausa não promete preservar escritas posteriores em eventual restauração humana.
7. Após deploy saudável, iniciar explicitamente somente face-gemma-index-worker pelo profile facial-gemma, com overlays existentes de monitor/branding apropriados, `--no-deps` e limites 6 GiB/1 CPU. Confirmar marcador, heartbeat e configuração global SFace. Nenhum backfill ou consulta com mídia real faz parte desta etapa.
8. Conferir healthchecks/estado dos recursos próprios e identidade/estado dos vizinhos, registrar SHA/schema e limitações; manter change ativa porque eficácia/calibração dependem do lote autorizado.

## Limits

Não há corpus real/ground truth/manifesto para benchmark. O limiar experimental ainda reutiliza configuração SFace. Não alegar eficácia, throughput multi-tenant ou liberação de produção pela validação sintética. Compatibilidade do runtime real e testes PostgreSQL ainda precisam de evidência nesta execução.

## Updated evidence

Worker geral retomado por procedimento existente e observado saudável. PostgreSQL sintético exclusivo validou migrations e foi descartado; nova instância sintética exclusiva foi criada para regressão concorrente, sem dados operacionais. Runtime ARM64 real passou offline após corrigir torchvision/template Jinja. Imagem final de validação: sha256:225e7151052429a68da064099803853c5345cd7f4ccbfa8ecf009a11faceea08, 3.185.235.004 bytes. Pico RSS 4.840,4 MiB e segunda inferência 34,402 s/1 CPU. Runtime é experimental, sem promessa de eficiência superior.

Backup pré-merge exclusivo verificado: pre-gemma-20261011T213949Z.dump, 21.795.803 bytes, modo 0600, SHA-256 3bbf117c5447e0937f609736eabab0776a49c5d1b3683b2fa9e165aaeac32807, pg_restore --list com 1.107 linhas. Ambiente permanece idêntico por verificação de hash; containers vizinhos mantêm as mesmas identidades. Nada foi restaurado/excluído no banco operacional.

Antes do merge, atualizar novamente checkout/schema/saúde/vizinhos. CI dedicated gemma-runtime valida AMD64 nativo e condiciona deploy; não usar Docker local sob pressão de memória nem modificar binfmt/kernel do servidor. O worker Gemma operacional terá limites 6 GiB/1 CPU, threads internas 1 e lease exclusivo 900 s. Nenhuma alteração de .env é necessária.

## Final state and continuation

PR #158 merged em develop, commit 6453eabc87a3f0c8fb09cb4f2e1ea8537bc35243; run 38181825031 concluído com CI/deploy verdes. Schema 0074, worker Gemma saudável e monitorado, imagem verificada, teto 6 GiB/1 CPU, lease 900 s e threads internas 1. Global SFace, primeira ativação ainda nula, zero jobs/vetores Gemma. Ambiente e vizinhos preservados; detalhes em validation.md.

Procedimento da primeira provisão de monitor, reproduzível a partir deste registro: ler o JSON/YAML seguro de /var/lib/markina-gallery/deploy-state/system-monitor.compose.yml; exigir entrada face-index-worker existente e monitor habilitado; copiar somente as chaves SYSTEM_MONITOR_* de política desse worker para uma nova services.face-gemma-index-worker.environment. Não sobrescrever entrada Gemma divergente. Criar backup exclusivo modo 0600 e candidato no mesmo diretório; verificar igualdade semântica de todas as entradas anteriores. Validar docker compose --env-file docker/.env.homolog -p markina-gallery com base, branding, definição preview-adjustment, overlay de código de monitor e candidato, profile facial-gemma, config --quiet. Somente depois substituir atomicamente o estado, sem editar .env; recriar apenas face-gemma-index-worker --no-deps/--no-build. Conferir flag efetiva, assets, heartbeat técnico, MonitorWorker recente, escolha SFace e recursos vizinhos. O overlay persistido agora contém essa entrada e é reutilizado pelos scripts em deploys/retomadas futuros.

O proprietário pode abrir /admin/settings e selecionar Usar Gemma para suas novas galerias autorizadas; antigas/incompletas ficam SFace. Eficácia e limiar ainda precisam de benchmark real; nenhum teste sintético autoriza produção ou fotografias arbitrárias. Não aplicar recomendações finais nem arquivar esta change sem seus dados/revisão humana.
