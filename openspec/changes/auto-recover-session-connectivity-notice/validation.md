# Validação

## Revisão pré-publicação — 11/10/2026

O proprietário autorizou prosseguir após receber o resultado local. A revisão identificou e corrigiu dois pontos antes da PR: a revalidação periódica de segurança prevista em `add-small-multi-photographer-pilot` foi preservada e erros de outras chamadas respeitam o backoff já agendado. A checagem de foco/retorno continua imediata. Não houve mudança de backend, schema ou credenciais.

Validação atual: **26 testes dirigidos**, **59 arquivos/476 testes frontend** aprovados; lint com zero erros e 37 avisos em arquivos não alterados; typecheck e build aprovados. OpenSpec estrito completo: **91 itens aprovados, zero falhas**. Os resultados de 24/474 abaixo são o checkpoint anterior à revisão.

Inventário somente leitura `38148908339` aprovado em 11/10/2026 às 14:53 UTC: SHA `d951235f50e9d557096e85d980ddcf2cf8b80268`, schema `20261009_0072`, 13 serviços saudáveis, entrada `127.0.0.1:8080`, subdomínio `markina-homolog.duckdns.org`, DB/Redis internos e volumes exclusivos; endpoints públicos de saúde HTTP 200 e filesystem em 47%. Nenhuma alteração persistente realizada pelo inventário.

Publicação planejada via PR para `develop`, checks do head e workflow existente com backup. A mudança não traz migration nem novas portas/volumes/credenciais. O workflow pode reiniciar serviços próprios da aplicação; projetos vizinhos, proxy, DNS e certificados permanecem fora do escopo. Sync/arquivo posteriores à comprovação da publicação, conforme mandato.

## Testes

- `cd frontend && npm test -- --run app/session-boundary.test.tsx` — **24 testes aprovados**. Inclui revalidação automática, remoção do aviso, erro isolado de operação, ausência de replay, pausa/retomada da aba, single-flight e teto de backoff de 30 s.
- `cd frontend && npm test` — **59 arquivos, 474 testes aprovados**. Uma execução inicial em paralelo com lint/typecheck/build apresentou uma falha no teste `app/admin/system-monitor/monitor.test.tsx`; o mesmo arquivo passou isoladamente (**10 testes**) e a suíte completa passou quando executada sem concorrência.

## Qualidade e build

- `cd frontend && npm run lint` — concluído sem erros; **37 avisos** existentes em outros arquivos (uso de `<img>`, parâmetros de teste e dependências de hooks). Nenhum aviso no `session-boundary.tsx` após remover o import sem uso.
- `cd frontend && npx tsc --noEmit` — aprovado.
- `cd frontend && npm run build` — aprovado com Next.js 16.3.2/Turbopack; rotas estáticas e dinâmicas geradas.
- `npx -y @fission-ai/openspec@1.14.0 validate auto-recover-session-connectivity-notice --type change --strict --no-interactive --json` — **1 change aprovada, 0 falhas**.
- `git diff --check` — aprovado.

## Limites da validação

Validação local de frontend; nenhuma publicação, deploy ou alteração de API foi feita. As verificações usam respostas sintéticas e não repetem pedidos reais, OTPs, compras ou uploads.
