# Tasks

## 1. Contrato de diagnóstico no backend

- [x] 1.1 Adicionar identificador aleatório validado, categoria de falha allowlisted e evento estruturado à rota de exclusão; verificar respostas mapeadas e inesperadas, rollback antes do commit e ausência de PII, SQL, parâmetros e segredo em corpo/log. Evidência: `backend/tests/test_admin_client_directory.py::test_unexpected_deletion_error_is_sanitized_and_correlated` passou; teste confirma UUIDv4 no corpo/cabeçalho, rollback, resposta/log sem telefone, SQL ou exceção bruta.
- [x] 1.2 Distinguir falha anterior ao commit de erro auxiliar posterior usando o recibo idempotente; verificar que resposta e repetição nunca afirmam rollback depois do commit nem repetem efeitos. Evidência: `test_post_commit_cleanup_error_returns_completed_receipt_and_reference` passou e confirmou recibo persistido, cliente removida e resposta HTTP 200 com limpeza pendente; `test_deletion_removes_exclusive_operational_graph_and_replays_receipt` passou na execução inicial do arquivo completo, cobrindo replay idempotente.
- [x] 1.3 Cobrir autenticação, bloqueio comercial, integridade, indisponibilidade e exceção inesperada com testes focados; registrar a evidência junto desta etapa e preservar os contratos existentes. Evidência: `python -m pytest tests/test_admin_client_directory.py -q` passou com 20 testes, incluindo exclusão não autorizada, bloqueio comercial, corrida de integridade, falha de banco/rollback e exceções inesperadas.

## 2. Mensagem na interface administrativa

- [x] 2.1 Preservar status e referência sanitizada no cliente HTTP; verificar exibição acessível do código em erro JSON e do status/falta de confirmação em resposta não JSON, sem renderizar HTML do proxy. Evidência: `frontend/app/admin/clients/client-directory.test.tsx` passou (8 testes), cobrindo UUID/status no JSON, HTTP 502 sem renderizar HTML e conclusão com limpeza pendente.
- [x] 2.2 Adicionar regressões de UI para bloqueio comercial, falha inesperada e confirmação ambígua; verificar que erro de transporte orienta recarregar a lista e não tenta excluir novamente. Evidência: mesma suíte passou; bloqueio comercial preservado, erro ambíguo orienta recarga, a lista mantém a cliente em falha e ocorre uma única chamada DELETE.

## 3. Integração e operação

- [ ] 3.1 Executar lint, testes backend/frontend focados, typecheck/build aplicáveis, OpenSpec estrito, gitleaks e revisão de diff; registrar resultados e assegurar que não há migration nem edição de configuração persistida.
- [ ] 3.2 Preparar inventário sanitizado e plano de impacto zero para homologação; aplicar a versão somente após autorização operacional explícita, conferir request ID/status em cenário sintético, preservar admin/Evolution e repetir a exclusão específica apenas após inventário atual elegível e confirmação devida. Parcial: inventário de referência, plano de impacto zero e probes públicos HTTP 200 em `homologacao-impacto-zero.md`; deploy e validação pós-publicação ainda pendentes.
