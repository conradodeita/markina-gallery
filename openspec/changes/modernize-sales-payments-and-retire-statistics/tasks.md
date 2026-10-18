# Tasks

## 1. Consulta e exportação

- [x] 1.1 Implementar filtro sintético priority e consulta reutilizada, CSV completo/seguro com confirmação real; testar autenticação, filtros, paginação e quatro colunas sem N+1; registrar evidência. Evidência: 10 testes backend de exportação/prioridades passaram; Ruff aprovado. Detalhes em validation.md.

## 2. Prévias e interface

- [x] 2.1 Disponibilizar derivados existentes por item autorizado de pedido; testar autenticação, associação, variantes, falta de derivado e remoção. Evidência: teste específico passou (10,80 s), servindo thumbnail/admin_preview exatos e 404 nos casos inválidos; headers privados preservados.
- [x] 2.2 Modernizar cards/detalhes/filtros, busca automática e exportação, preservando ações existentes; testar seleção mouse/Enter, Todos, limpar, combinações, erros e cursor. Evidência: 30 testes frontend passaram (13,26 s); novo arquivo redesign.test.tsx cobre autoaplicação por mouse/Enter, filtros prioritários/Todos/limpar e feedback CSV.
- [x] 2.3 Implementar miniaturas sob demanda e lightbox modal acessível; testar abrir/navegar/fechar, estados de imagem, foco e preservação de contexto. Evidência: 32 testes do diretório passaram, typecheck/lint aprovados; nova regressão de montagem sob demanda + modal: 7 testes passaram (5,24 s). Validação em navegador fica no checkpoint de integração.

## 3. Aposentadoria e integração

- [x] 3.1 Remover dependências comprovadamente exclusivas de Estatísticas após inventário, com teste de menu/404 e regressão de métricas compartilhadas; documentar recursos preservados. Evidência: oito rotas backend antigas verificadas com 404; testes de navegação/ausência da rota e consulta financeira compartilhada passaram; Ruff aprovado. Inventário em validation.md.
- [x] 3.2 Executar testes de integração, lint, typecheck, build e OpenSpec; revisar diff incremental e entregar relatório técnico com resultados/limitações. Evidência: 39 backend passaram/5 PostgreSQL pulados; 45 frontend passaram; typecheck, lint dirigido, Ruff, build e OpenSpec aprovados; 6 cenários de navegador com fixtures e 18 capturas. Relatório A–H entregue em RELATORIO_IMPLEMENTACAO_VENDAS_PAGAMENTOS.md; limites de ambiente/aceite visual em validation.md e design-qa.md.
- [x] 3.3 Reconciliar o verificador de release API/web com os caminhos exatos de Vendas e pagamentos e a aposentadoria exata de Estatísticas; manter allowlist fechada e manifests com hashes dos runtimes candidatos, sem alterar baseline ou gates de produção; testar classificação, escopo e política completa. Evidência: 8 testes do escopo API/web, 7 gates faciais, 12 cenários de classificação e 7 testes de inventário passaram; regressões Bash API/web/facial e política de workflow passaram; classificador do candidato reportou `app_release_ready=true`, `somente_api_web`; OpenSpec estrito aprovado.

## Workflow follow-up

- Revisão e autorização humana recebidas em 18/10/2026. Specs principais de `payment-operations-dashboard` e `sales-statistics` sincronizadas; arquivar a change depois de integrar o PR da implementação. A publicação permanece sujeita a inventário do SHA final e aos gates de API/web.
