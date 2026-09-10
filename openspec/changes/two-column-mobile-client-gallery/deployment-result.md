# Resultado do deploy em homologação

## Identificação

- Ambiente: `homolog`
- Subdomínio: `markina-homolog.duckdns.org`
- Workflow: `34433083251`
- Pull request: `#61`
- Merge SHA publicado: `40cde8fd955895fae366484d6899f014b2a951bc`
- Conclusão do workflow: sucesso

## Gates e implantação

- `gitleaks`: sucesso
- OpenSpec: sucesso
- frontend: sucesso
- backend: sucesso
- `deploy-homolog`: sucesso após aprovação humana previamente concedida
- Backup lógico exclusivo da Markina criado antes da publicação.
- Migration permaneceu em `20260909_0052 (head) -> 20260909_0052 (head)`, sem alteração de schema.
- `FACIAL_PROCESSING_ENABLED` já estava persistido como `true` e permaneceu `true`.
- Workers `face-index-worker`, `face-search-worker` e `face-maintenance-worker` ficaram saudáveis.

## Preservação e ausência de backfill

O deploy não chamou endpoint administrativo de regeneração, não reenfileirou prévias e não executou reindexação facial. O inventário final registrou:

- `637` fotos no banco;
- `637` arquivos-fonte;
- `1.911` derivados;
- `0` arquivos no histórico.

Isso preserva o acervo de teste existente. O novo comportamento de marca-d'água será aplicado apenas a prévias geradas futuramente pelo fluxo normal ou por uma ação administrativa futura e deliberada.

## Saúde pós-deploy

- `GET /healthz`: HTTP 200 (`ok`)
- `GET /api/health`: HTTP 200 (`status=ok`, `service=api`)
- `GET /`: HTTP 200
- API, banco, Redis, web, worker, Nginx e workers faciais: saudáveis no inventário do deploy.

O Compose informou um container facial legado órfão já existente. Ele foi preservado, sem `--remove-orphans`, conforme o plano de impacto zero e a proibição de remover recursos fora do escopo.

## Aceite restante

A implementação e o deploy estão concluídos. A sincronização da spec principal e o arquivamento da change permanecem pendentes da revisão visual humana descrita em `homologation-checklist.md`, especialmente:

1. duas colunas em aparelho real nos viewports de `320`, `360` e `390 px`;
2. uma nova prévia exibindo o texto personalizado uma única vez;
3. grade de proteção visualmente inalterada.
