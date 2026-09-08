# Inventário e plano de produção da busca facial

Data: 2026-09-08. Este inventário foi produzido somente a partir do repositório e da configuração Compose renderizada localmente. Nenhum host de produção foi acessado ou alterado. Campos que exigem inspeção imediatamente anterior no servidor permanecem explicitamente pendentes.

## Estado da candidata

- branch candidata: `feature/productionize-facial-search`;
- base `develop` na abertura do PR: `eeb9147f41a3ed53bef0d566ab39f415ddcee150`;
- Pull Request de homologação: `#52`, com destino `develop`;
- SHA raiz da change: `30fc5bdfa06984ec2220dd4085b6360ef7b94621`; o SHA publicável será o HEAD final aprovado do PR;
- CI inicial do PR: `backend`, `frontend`, `openspec` e `gitleaks` aprovados; `deploy-homolog` corretamente ignorado em evento `pull_request`;
- migration head: `20260908_0051`;
- primeiro deploy de produção: MUST usar `FACIAL_PROCESSING_ENABLED=false`;
- domínio/subdomínio de produção: não definido no repositório;
- inventário real do host, capacidade livre, backup imediatamente anterior e configuração externa: pendentes.

O SHA candidato acima é publicável apenas em homologação após merge aprovado em `develop`. Ele não constitui aprovação de produção, canary ou fluxo infantil; o candidato de produção continuará pendente de merge/revisão em `main` e dos gates descritos neste documento.

O workflow de `develop` solicita explicitamente `FACIAL_PROCESSING_ENABLED=true` somente em homologação. O deploy registra inventário Markina antes dessa alteração, persiste a flag atomicamente, inicia as três classes de worker sem portas e restaura o estado anterior em falha; defaults locais e o primeiro deploy de produção continuam `false`.

## Projeto, serviços e isolamento

Toda operação usa `-p markina-gallery -f docker/docker-compose.yml` e somente recursos desse projeto.

| Grupo | Serviços | Exposição/limite conhecido |
| --- | --- | --- |
| borda | `nginx` | única porta publicada pelo Compose; default local `8080:80`; produção SHALL definir binding aprovado e confirmar o subdomínio |
| aplicação | `web`, `api`, `worker`, `migrate` | `web:3000` e `api:8000` apenas expostos na rede interna, sem porta de host |
| dados | `db`, `redis` | somente rede interna, sem porta de host |
| facial | `face-search-worker`, `face-index-worker`, `face-maintenance-worker` | profile `facial`, zero portas; respectivamente 0,75/1,0/0,25 CPU e 512/768/256 MiB |

O teto facial configurado soma 2 CPU e 1.536 MiB. Ele não constitui aprovação de capacidade: CPU/memória livres e contenção com os demais projetos SHALL ser medidas no host, e a task ARM 6.4 permanece pendente.

Volumes do projeto: `pgdata`, `redisdata`, `media-source`, `media-derivatives`, `media-history` e `facial-references`. Redes: `internal` e a rede externa de proxy `npm`. O inventário imediatamente anterior SHALL confirmar nomes resolvidos, ownership, mounts, membros de rede e que nenhum recurso de terceiro será criado, removido ou reconectado.

## Portas, domínio e healthchecks

- validar binding real de `MARKINA_GALLERY_PORT`; o valor default do repositório é `8080:80` e não deve ser presumido adequado ao host;
- confirmar o subdomínio exclusivo de produção e o encaminhamento existente antes de qualquer alteração;
- não editar proxy, firewall, DNS ou certificado sem inventário e autorização específicos;
- confirmar healthchecks de `nginx`, `web`, `api`, `db`, `redis`, `worker` e das três classes faciais;
- executar smoke sem PII em `/healthz` e `/api/health`; a cliente e o administrador continuam no fluxo manual enquanto a flag estiver falsa.

## Backup e migrations

O deploy cria `pg_dump -Fc` exclusivo da Markina em `/var/lib/markina-gallery/backups` antes da troca de SHA e grava manifesto com SHA anterior/alvo. O caminho, permissões, espaço, checksum e restauração previamente testada SHALL ser confirmados no host. Restauração nunca é automática. Backup diário cifrado externo continua pendente da change `media-storage` e não deve ser declarado existente sem evidência.

As migrations `0048` a `0051` são aditivas: rollout, representação legal, aprovação de calibração e recibo operacional. O deploy SHALL registrar revisão anterior, executar `upgrade head`, confirmar exatamente `20260908_0051` e impedir rollback automático de código se houver divergência de schema.

## Gates antes do canary

| Gate | Estado em 2026-09-08 | Evidência/remanescente |
| --- | --- | --- |
| segurança | verde local | revisão sem achado crítico/alto e gitleaks sem vazamento |
| privacidade/retenção | verde local | AEAD/AAD, autorização repetida, purge e direitos testados |
| base legal | pendente humano/jurídico | referência técnica existe; decisão e validade de produção não foram fornecidas |
| calibração/equidade | bloqueado | gate fail-closed pronto; falta corpus permitido representativo e aprovação humana |
| capacidade ARM | bloqueado | ensaio local de 100 aprovado; falta carga autorizada no host compartilhado |
| recuperação | parcialmente verde | runbook e rollback local testados; backup/restauração e inventário do host pendentes |
| aprovação humana | pendente | nenhuma autorização desta conversa substitui o inventário imediatamente anterior e o SHA publicável |
| fluxo infantil | bloqueado | exige representação, consentimento e aprovação jurídica/humana; nenhuma flag isolada habilita |

Enquanto qualquer gate estiver pendente, produção permanece em `dark`/flag falsa e a seleção manual permanece disponível.

## Canary proposto

1. Publicar o SHA aprovado com a flag falsa e sem workers faciais ativos.
2. Validar schema, modelos, chave exclusiva de produção, configuração, portas, healthchecks, métricas e smoke sem PII.
3. Preparar rollout `dark` para uma allowlist mínima de Galerias públicas explicitamente aprovada.
4. Após gates verdes e nova confirmação, ligar o kill switch e ativar `canary` somente para a mesma allowlist por operação protegida.
5. Observar admissão, p95, filas, falhas, purge, CPU e memória pelo período aprovado; não usar IDs, imagens, vetores ou scores em métricas.
6. Promover somente por novo recibo e aprovação; o fluxo infantil permanece fora do canary até seu gate próprio.

## Rollback de impacto zero

No primeiro alerta crítico, suspender a allowlist afetada; para risco sistêmico, desligar o kill switch. Bloquear novas admissões, manter `maintenance` quando seguro e comprovar referências/candidatas/índices em contagens agregadas. Restaurar somente código e containers Markina ao SHA anterior se o schema permanecer compatível; nunca restaurar banco automaticamente. Fotos, seleção manual, pedidos, pagamentos e mídia histórica permanecem disponíveis.

A operação SHALL NOT executar `down`, prune, migration destrutiva, remoção de volume/rede, alteração de proxy/firewall/DNS/certificado ou qualquer ação em recurso de terceiro. Uma autorização de deploy futuro deverá citar o SHA integral, inventário do host, subdomínio/binding, referência opaca do backup, etapa, allowlist, gates e confirmação explícita.
