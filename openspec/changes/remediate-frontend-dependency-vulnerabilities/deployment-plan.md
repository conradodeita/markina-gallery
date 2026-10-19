# Plano de publicação da correção do frontend

## Resultado final — 19/10/2026

**PUBLICADO**: frontend do SHA `4b464f081dfa2451472848622853460398834e6d`, imagem `sha256:6aef1935d8a4ba4bfc125a1bf5bea52ae6e26db361ef4942a1fedc55c4efc20a`. Publicação às 11:04:45 UTC; verificação independente final às 11:08:13 UTC. A correção está disponível aos clientes. Ver [relatório operacional e evidências](production-publication-2026-10-19.md).

## Escopo executado

- Produto Pick-your-Pic, projeto Compose `markina-gallery`, domínio `markina.pickyourpic.com.br`; entrada Nginx `127.0.0.1:8080`, web interna `3000/tcp`.
- Atualização somente web pelo [runbook](../../../docs/DEPLOY-PROD-WEB.md), após autorização do SHA exato e gates de identidade/proveniência, Compose, saúde, recursos, concorrência e recuperação.
- API, banco/migrations, workers, Redis, Nginx/proxy, volumes/fotografias, ambiente/segredos e terceiros preservados. O nome histórico `.env.homolog` não torna descartáveis os dados reais deste ambiente.

## Engenharia e integração concluídas

A proposta do PR #177 para develop foi reaplicada em candidato isolado baseado em main. O [PR #226](https://github.com/conradodeita/markina-gallery/pull/226) integrou somente manifests/lockfile e OpenSpec em `81eb0741ab824a74a1f2b4f3df4dfb86da81b5c5`, com [CI aprovado](https://github.com/conradodeita/markina-gallery/actions/runs/39167932644). Vendas/pagamentos e remoção de Estatísticas preservados.

No candidato de main, instalação reproduzível, lint, typecheck e build passaram; a repetição completa do Vitest aprovou 63 arquivos/562 testes, após falha transitória investigada. Code Review local sem apontamentos acionáveis. Lockfile: Next/eslint-config-next 16.4.0, sharp 0.35.5 e source-map-js 1.2.2. Auditoria runtime zero; auditoria completa cinco altas/zero críticas na cadeia dev ESLint/braces. O downgrade incompatível sugerido pelo remédio automático não foi aplicado. Estes são resultados daquela auditoria, não uma nova consulta de advisories.

O PR #227 formalizou identidade, adoção, inventários sem escrita, locks sem truncamento e recuperação por ID. A primeira publicação foi bloqueada por Health ausente em migrate parado, antes de modificar o runtime. O PR #228 corrigiu o campo opcional, mantendo todos os containers e verificações obrigatórias; 35 contratos e todos os checks passaram. As integrações tiveram release_scope=none e não acionaram deploy. Histórico completo e links de CI estão no relatório operacional.

PR #177 e develop preservados. O merge em develop usa deploy amplo com API/worker/migrate e não foi utilizado nesta manutenção. Integrar #177 não é etapa desta publicação já concluída.

## Validação e rollback

A imagem anterior `sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573`, originada em `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`, foi preservada sob referência dedicada conferida por ID. Recibos/histórico atualizados; marcadores app/global preservados.

15/15 serviços ativos saudáveis, migrate histórico parado intacto; todos os não-web mantiveram IDs/imagens/início/configuração/montagens. HTTPS saúde/API/raiz/pagamentos 200, Estatísticas 404; versões e asset público conferidos no container novo. Sem OTP ou transação financeira real. Rollback-inventory comprovou recuperação da imagem/checkout anteriores exatos; rollback não necessário nem executado.

## Pendências e autorizações futuras

Nenhuma pendência impeditiva dessa publicação identificada. Cinco alertas altos dev permanecem documentados. Sincronização/arquivamento aguardam revisão humana. A consolidação atual publica somente documentos; nova publicação/escrita Oracle exige autorização específica e repetição dos gates mutáveis, sem reutilizar aprovações históricas.
