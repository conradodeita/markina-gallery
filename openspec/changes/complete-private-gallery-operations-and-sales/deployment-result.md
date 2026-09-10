# Resultado do deploy em homologação

## Publicação

- Ambiente: `homolog`
- Subdomínio: `markina-homolog.duckdns.org`
- GitHub Actions: run `34428359868`, job `102719291507`
- Merge SHA publicado: `f8dadced20ba36be619141f48115be88ede95775`
- Estado do deployment GitHub: `success`
- Horário de conclusão: `2026-09-10T02:17:39Z`

## Evidências automáticas

- O job criou backup lógico exclusivo da Markina antes da migration.
- A migration avançou de `20260908_0051` para `20260909_0052`.
- `FACIAL_PROCESSING_ENABLED` permaneceu persistido como `true`.
- O deploy confirmou estado facial coerente com os três workers faciais saudáveis.
- API, web, nginx, PostgreSQL, Redis, worker geral e serviços Evolution permaneceram saudáveis.
- A entrada externa permaneceu isolada em `127.0.0.1:8080`; PostgreSQL e Redis não ganharam portas públicas.
- Os checks externos `GET /healthz`, `GET /api/health` e `GET /` responderam HTTP `200` após o deploy.
- O inventário pós-deploy preservou `1` cliente, `1` Galeria pública, `1` galeria privada, `1` pedido e `637` fotos. O armazenamento preservou `637` arquivos-fonte e `1911` derivados; nenhuma limpeza foi executada.
- O Compose informou o container legado órfão `markina-gallery-face-worker-1`; a automação não o removeu, em conformidade com o plano de impacto zero.

## Revisão humana pendente

A task 9.4 permanece aberta até o proprietário validar, em sessão autenticada:

1. upload de JPEG novo do dispositivo para pasta própria da galeria privada;
2. contadores `Fotos no acervo privado`, `Fotos selecionadas` e `Fotos compradas`;
3. congelamento após expiração e solicitação/decisão de reabertura;
4. área `Vendas e pagamentos`, incluindo comunicação, confirmação e correção;
5. responsividade e operação em desktop e smartphone.

Não havia sessão administrativa aberta no navegador compartilhado durante a conferência pós-deploy. Nenhum login, OTP, dado ou mutação artificial foi criado para substituir a revisão humana.

## Próximo gate

Somente após o aceite humano os delta specs SHALL ser sincronizados às specs principais e a change poderá ser arquivada.
