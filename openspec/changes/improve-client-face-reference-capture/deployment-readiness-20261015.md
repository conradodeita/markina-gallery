# Preparação de produção — 2026-10-15

## Estado atual

- Candidata: PR #192, branch `codex/improve-client-face-reference-capture`, baseada exatamente no SHA de produção `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`. O código do SHA `9891afb06f74722fd3aaabcd50b09fa4905164b1` passou CI GitHub #38815751058; o PR ainda está aberto e não foi integrado à `main`.
- O environment GitHub `production` foi configurado: revisor obrigatório `conradodeita`, branch permitida somente `main`, bypass administrativo desativado. Secrets adicionados a partir do arquivo SSH fornecido pelo proprietário: `PRODUCTION_SSH_PRIVATE_KEY` e `PRODUCTION_SSH_KNOWN_HOSTS`. Variáveis: `PRODUCTION_SSH_HOST`, `PRODUCTION_SSH_PORT`, `PRODUCTION_SSH_USER` e `PRODUCTION_PUBLIC_BASE_URL`. Nenhum valor privado foi exibido.
- Inventário remoto somente de leitura coletado em `2026-10-15 23:13:51 UTC` com a chave fornecida. Nenhum comando de mutação foi executado.

## Revalidação somente leitura — 2026-10-16 01:34:44 UTC

- Host `clearbudget-vnic`, arquitetura `aarch64`, 4 CPUs; load `0.20 0.22 0.13`; RAM disponível `21.507.387.392` bytes; `/var/lib/docker` com `77.945.286.656` bytes livres (63% usado).
- Checkout `/opt/markina-gallery` continuava limpo em `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`; Compose do projeto `markina-gallery`; Nginx somente em `127.0.0.1:8080`, API `8000/tcp` e web `3000/tcp` internos. Os serviços Markina listados pelo Compose estavam saudáveis; Evolution permaneceu fora do escopo.
- `https://markina.pickyourpic.com.br/healthz`, `/api/health` e `/` retornaram HTTP 200.
- O backup mais recente observado foi `predeploy-20261015T164654Z-71be3b296591.dump`, 71.128.950 bytes, modo `0600`, dono `ubuntu:ubuntu`, SHA-256 `549b6f6861f54a2280b521aa67bcf17db2be50ea93dd00628fe68f67f42a9f45`; seu manifesto aponta os SHAs anterior `350a802e9f8894a180a5beb1500db9ba50c8fded` e alvo `71be3b29659143293351968e15fb4886c2d72bf0`. Nenhuma restauração foi feita. `pg_restore` não está instalado no host e o arquivo não está montado no container PostgreSQL, então integridade restaurável não foi verificada.
- O snapshot de recursos não é ensaio de carga e não aprova capacidade ARM. Nenhuma mutação, build, restart, consulta facial ou carga foi executada.

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

## Fluxo automático no GitHub

- O CI roda em PR e em push para develop ou main. Um PR verde não publica nada; o merge gera um único evento push em main, e o job de preflight começa no mesmo run depois dos jobs obrigatórios. Não é necessário um segundo push para destravar deploy.
- O preflight usa o environment separado `production-preflight` e uma chave dedicada, sem revisores, para fazer inventário remoto somente leitura. O wrapper root-owned valida a revisão e o comando forçado, busca o script de inventário por SHA imutável, confere o blob Git fixado e só permite `--mode inventory`; o fingerprint liga SHA, containers, imagens, configuração e domínio.
- Em 2026-10-16, o wrapper root-owned foi instalado com hash conferido, a chave ED25519 dedicada foi registrada em `authorized_keys` com `restrict`/comando forçado, e o environment `production-preflight` foi configurado somente para `main` com variáveis/secrets dedicados. O teste negativo comprovou que `whoami` é recusado. O teste positivo aguarda o merge para que o script pinado esteja no HEAD de `main`; nenhum serviço de aplicação foi tocado.
- O workflow avalia `production-gates.json`. Enquanto qualquer gate não tiver status aprovado e referência de evidência verificável, `production-release` é ignorado; nenhum comando mutável é enviado ao host.
- Quando todos os gates forem aprovados, o segundo job aguarda nova aprovação do environment production, após o inventário estar visível na mesma execução. Ele refaz as verificações e exige que o fingerprint ainda corresponda antes de construir e recriar somente web, api e face-search-worker.
- O script não executa migration e falha se Compose, Docker ou migrations mudarem entre o SHA ativo e o alvo. Em caso de falha operacional não há rollback automático; imagens anteriores ficam etiquetadas e o rollback exige inventário e aprovação próprios.
- Estado atual de `production-gates.json`: bloqueado por base legal, calibração/equidade e representação/consentimento infantil sem evidência humana. O snapshot de ARM foi registrado, mas falta carga autorizada; recuperação continua parcial porque backup e manifesto existem, mas restauração não foi verificada. Aprovação operacional também segue pendente. O preflight pode inventariar após CI verde e credencial dedicada; nenhum release é permitido até que cada gate exigido tenha status aprovado e evidência verificável.

## Atualização pós-merge — 2026-10-16

- A PR #192 foi integrada automaticamente à `main` como `b191e1c` depois do CI #38836929107 passar. Não houve push extra para provocar merge.
- No run da `main` #38839154615, os seis checks de CI passaram. O job `production-preflight` parou antes do SSH porque o checkout padrão raso não continha `b191e1c^`; o erro `fatal: bad revision` veio da comparação local que protege alterações em Compose e migrations. O inventário remoto não foi executado e nenhum serviço foi alterado.
- A PR #193 integrou a correção de profundidade 2 no checkout do preflight. No run da `main` #38844941508, os seis checks passaram e a verificação local foi superada. O inventário remoto, porém, abortou ao encontrar hash Compose divergente em `api`; uma conferência separada somente de leitura confirmou que `web` corresponde e `api` e `face-search-worker` divergem. Nenhum fingerprint completo foi gerado e nenhum serviço foi alterado. `production-release` foi ignorado pelos gates faciais ainda sem aprovações válidas. A divergência precisa ser investigada e reconciliada com plano operacional próprio antes de repetir o preflight.

## Gates que impedem a execução

1. Revalidar os gates da change `productionize-facial-search`: base legal, calibração/equidade com corpus autorizado, capacidade ARM, recuperação e o gate próprio de representação/consentimento para fluxo infantil. O registro versionado em `docs/PRODUCAO-FACIAL-INVENTARIO-E-PLANO.md` os mantém pendentes ou bloqueados; a flag atualmente ativa não os satisfaz.
2. Implementar e validar workflow e preflight multi-serviço fail-closed sem permitir que secret ausente, inventário divergente ou aprovação ausente cause mutação.

Até esses gates serem resolvidos e o inventário ser aprovado, não iniciar deploy nem habilitar a busca facial em produção.
