# Resultado do deploy em homologação

## Entrega

- PR: `#69`.
- Branch integrada: `feature/auto-enable-facial-processing-new-galleries`.
- SHA publicado: `43c0d017ffdcc8891da24be31d770b957dbc2b41`.
- Workflow: `34661773053`.
- Job de deploy: `103466628138`.
- Resultado: concluído com sucesso em 2026-09-12.

## Evidências de paridade

- O workflow confirmou o SHA esperado no checkout de `develop` e concluiu o deploy desse mesmo SHA.
- A migration permaneceu inalterada em `20260910_0053 (head) -> 20260910_0053 (head)`.
- O gate operacional confirmou `flag=true` e workers faciais saudáveis antes e depois da publicação.
- `markina-gallery-face-index-worker-1`, `markina-gallery-face-search-worker-1` e `markina-gallery-face-maintenance-worker-1` reiniciaram e alcançaram estado `healthy`.
- `https://markina-homolog.duckdns.org/healthz` respondeu HTTP 200.
- `https://markina-homolog.duckdns.org/api/health` respondeu HTTP 200.
- A entrada pública da galeria de homologação respondeu HTTP 200.

## Impacto observado

- Nenhuma migration, escrita em massa, duplicação, exclusão ou reprocessamento retroativo de mídia foi executado.
- A publicação preservou a topologia Markina e não alterou proxy, DNS, certificado, firewall ou recursos de terceiros.
