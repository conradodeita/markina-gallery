# Preparação de produção — 2026-10-15

## Estado atual

- Candidata: PR #192, branch `codex/improve-client-face-reference-capture`, baseada exatamente no SHA de produção `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`. O código do SHA `9891afb06f74722fd3aaabcd50b09fa4905164b1` passou CI GitHub #38815751058; o PR ainda está aberto e não foi integrado à `main`.
- O environment GitHub `production` foi configurado: revisor obrigatório `conradodeita`, branch permitida somente `main`, bypass administrativo desativado. Secrets adicionados a partir do arquivo SSH fornecido pelo proprietário: `PRODUCTION_SSH_PRIVATE_KEY` e `PRODUCTION_SSH_KNOWN_HOSTS`. Variáveis: `PRODUCTION_SSH_HOST`, `PRODUCTION_SSH_PORT`, `PRODUCTION_SSH_USER` e `PRODUCTION_PUBLIC_BASE_URL`. Nenhum valor privado foi exibido.
- Inventário remoto somente de leitura coletado em `2026-10-15 23:13:51 UTC` com a chave fornecida. Nenhum comando de mutação foi executado.

## Inventário atual

| Item | Observação somente de leitura |
| --- | --- |
| Host / arquitetura | `clearbudget-vnic`, ARM64 (`aarch64`), 4 CPUs |
| Checkout | `/opt/markina-gallery`, árvore limpa, detached HEAD em `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`; `origin/main` aponta para o mesmo SHA |
| Projeto | Compose `markina-gallery`, arquivo `docker/docker-compose.yml`; nenhum recurso fora do projeto foi consultado ou alterado |
| Domínio / porta de entrada | `https://markina.pickyourpic.com.br`; Nginx do projeto ligado a `127.0.0.1:8080 -> 80` |
| Serviços da aplicação | API `8000/tcp` interno, web `3000/tcp` interno, workers sem portas publicadas |
| Schema | Alembic `20261014_0081`; nenhuma migration está prevista nesta change |
| Flag facial | `FACIAL_PROCESSING_ENABLED=true` na configuração da API em execução |
| Saúde externa | `/healthz`, `/api/health` e `/` retornaram HTTP 200 |
| Recursos do host no instante da coleta | load `0.18 0.16 0.11`, memória total 25.154.072.576 B / disponível 21.603.766.272 B, `/var/lib/docker` com 76.141.028 KiB livres (63% usado) |

Containers alvo observados, todos `running/healthy`:

| Serviço | Container ID | Image ID | Hash Compose |
| --- | --- | --- | --- |
| `api` | `ac8b5d76d72fd914f000b9038944f285135fb0fe914ccf2e907712f4b83826b0` | `sha256:d353d21d4974c8a8b08a34740c147e3594b989152bc49e72459372aa203c5cf0` | `965953387b335840e3e4ce8c86a0e96bfef855932894fcc290a34cbf06761535` |
| `web` | `cdc0ec2303704bc9043040f5e2ba65834aa5273ff43d5cc9cb844d09137cc3ce` | `sha256:82df90ce3a383673872eb8847beb2d421a36f6983d3c50a7794f6fb28e069bec` | `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05` |
| `face-search-worker` | `ccd3097209175eeb63ed852872e82b738556d3cb78b3ce136a8561899b8eee63` | `sha256:895e167001f84cfdbd9f53559b3fe6773e77eeb03fd1556b1e5eeceaca7b6ef7` | `24b086aa936e0e17b9611ed928b57a6e28763c217f414fc7e801ef640706b570` |

Também estavam saudáveis os serviços Markina de Nginx, banco, Redis, workers facial de indexação/manutenção e demais workers. O container one-shot `markina-gallery-migrate-1` permanece `Exited (255)` desde duas semanas antes, embora o schema corrente seja `20261014_0081`; ele não será iniciado nem alterado por esta change. Evolution e seus containers permanecem fora do escopo.

Os dados são uma fotografia do host no horário indicado; repetir inventário, hashes, saúde, capacidade e flag imediatamente antes do release. A flag facial ativa diverge do documento de gates versionado, então não deve ser interpretada como aprovação ou evidência de que os gates foram concluídos.

## Escopo e impacto esperado

A change altera o frontend da câmera, a API/provedor de referência facial e o worker de busca. O conjunto candidato é `web`, `api` e `face-search-worker`. Não há migration de banco nem reindexação. O plano não inclui `db`, `redis`, `migrate`, proxy compartilhado, DNS, firewall, certificados, redes, volumes, Evolution ou qualquer recurso de outro projeto.

Mesmo limitado ao projeto `markina-gallery`, recriar API/web pode causar breve indisponibilidade e reiniciar o worker pode atrasar jobs de busca. Não prometer zero downtime. Se CPU, memória ou disco compartilhados não comportarem a construção, a operação deve parar antes de substituir containers saudáveis.

## Plano preliminar de execução e reversão

1. Resolver os gates faciais e atualizar este inventário no host imediatamente antes da execução: SHA `main` integral, árvore remota, migrations, containers/healthchecks, imagens reais, configuração efetiva comparada em memória, domínio/bindings, capacidade, backup disponível e isolamento dos recursos Markina. Não imprimir nem persistir configurações com segredos.
2. Apresentar inventário atualizado, impacto, possível interrupção e SHA alvo ao proprietário e obter aprovação explícita para essa execução. A aprovação do environment GitHub, por si só, não substitui a aprovação do plano específico.
3. Construir as imagens do SHA aprovado antes de substituir containers; usar exclusivamente `docker compose -p markina-gallery -f docker/docker-compose.yml` e apenas os serviços confirmados como necessários. Preservar IDs/imagens anteriores e parar se configuração, SHA, serviços ou recursos divergirem.
4. Substituir somente os serviços aprovados, validar saúde interna e HTTPS de `/healthz`, `/api/health` e `/`. O worker pode atrasar jobs durante a troca; não expor imagens, embeddings, scores ou PII nos logs.
5. Se a saúde falhar, interromper o rollout, apresentar diagnóstico e novo plano de recuperação. Restaurar somente as imagens Markina previamente registradas após aprovação explícita; nunca restaurar banco automaticamente nem tocar recursos compartilhados.

## Gates que impedem a execução

1. Revalidar os gates da change `productionize-facial-search`: base legal, calibração/equidade com corpus autorizado, capacidade ARM, recuperação e o gate próprio de representação/consentimento para fluxo infantil. O registro versionado em `docs/PRODUCAO-FACIAL-INVENTARIO-E-PLANO.md` os mantém pendentes ou bloqueados; a flag atualmente ativa não os satisfaz.
2. Implementar e validar workflow e preflight multi-serviço fail-closed sem permitir que secret ausente, inventário divergente ou aprovação ausente cause mutação.

Até esses gates serem resolvidos e o inventário ser aprovado, não iniciar deploy nem habilitar a busca facial em produção.
