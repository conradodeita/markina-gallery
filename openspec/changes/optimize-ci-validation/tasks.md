# Tasks

## 1. Inventário e desenho
- [x] 1.1 Medir baseline e comprovar repetições/configurações distintas. Evidência: run 40397675011 e comandos/fixtures registrados em design.md; preservar a variante DATABASE_URL PostgreSQL.

## 2. Implementação
- [x] 2.1 Implementar partição determinística por módulo e agregação de manifestos; validar cobertura/disjunção, coleção divergente, partes ausentes/vazias e parâmetros inválidos com testes focados. Evidência: nove testes novos passaram, incluindo subprocessos pytest reais com parametrização, fixture de módulo, skip e falha.
- [x] 2.2 Distribuir suíte em três runners isolados, separar qualidade e preservar check backend e variante PostgreSQL; validar contrato YAML e gates de release existentes. Evidência: parser YAML confirmou matriz 0/1/2, serviços/variáveis idênticos, dependências do agregador e ausência de continue-on-error; política de release passou. Todos os jobs a partir de frontend permanecem textualmente iguais ao baseline 8dcb0299.
- [x] 2.3 Publicar diagnóstico de duração e documentar execução, custo e recuperação; revisar diff por duplicações, omissões e alteração indevida de runtime. Evidência: docs/CI-VALIDATION.md, JUnit/manifestos e --durations=25 configurados; somente workflow/helpers/docs/OpenSpec alterados.

## 3. Validação e publicação
- [x] 3.1 Executar testes focados, integração sintética pytest, lint, validação OpenSpec estrita e diff-check; registrar evidências. Evidência: 26 testes (backend_ci, check_ci_results, classify_ci_scope) passaram; ruff dos dois arquivos novos, production release workflow policy, OpenSpec strict e git diff --check passaram. A coleção real e o desempenho completo serão comprovados no runner Linux na tarefa 3.2.
- [x] 3.2 Publicar PR, acompanhar CI no SHA exato e medir resultado por parte, mantendo pendente qualquer evidência remota indisponível. Evidência: PR #300 SHA dbd4f74ce5bae0869eb58410932b05548560569e, CI 40406191752 success; partes 8min12s, 5min58s e 8min13s, qualidade 1min38s e agregador 5s; 1600 itens coletados exatamente uma vez, 1577 passaram e 23 skipped, comparáveis ao baseline de 32min. A alteração documental desta evidência gera outro SHA que requer novo CI antes do merge.

## Workflow follow-up
- Integrar conforme autorização após CI verde e coordenação com release 0090. Não arquivar/sincronizar specs sem revisão humana.
