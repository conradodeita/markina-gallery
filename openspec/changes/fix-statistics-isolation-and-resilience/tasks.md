# Tasks

## 1. Contrato e agregação

- [x] 1.1 Corrigir o escopo por cliente em pedidos e seleções compartilhadas e cobrir filtro combinado por cliente/galeria/evento; verificar com regressão backend de membro compartilhado. Evidência: `pytest -q tests/test_derived_galleries.py -k "statistics"` aprovou 2 testes, incluindo cliente membro de galeria compartilhada sem dados cruzados.
- [x] 1.2 Usar snapshots textuais para compras confirmadas cujo ativo operacional foi removido e garantir IDs válidos nos dois TXT; verificar com regressão backend de item sem FK e exportação UTF-8. Evidência: a mesma regressão aprovou ID `photo_asset_id_snapshot`, nome congelado e ausência de PII no TXT.
- [x] 1.3 Adicionar totais e offsets independentes para as listas HTML, preservando compatibilidade dos campos existentes e exports completos; verificar com regressão backend de offsets e contagens. Evidência: a regressão consultou `purchased_offset` e `selected_offset` separadamente e confirmou `purchased_total`.

## 2. Interface administrativa

- [x] 2.1 Implementar paginação independente de compradas e selecionadas, reiniciando a página quando os filtros forem aplicados; verificar com teste Vitest dos controles e query string. Evidência: teste frontend confirma botão `Próxima`, item da segunda página e `purchased_offset=50`.
- [x] 2.2 Diferenciar erro de consulta de estado vazio, com retry acessível e filtros preservados; verificar com teste Vitest de falha e nova tentativa. Evidência: teste frontend confirma `role="alert"`, ausência de `R$ 0,00` falso e segunda tentativa bem-sucedida.

## 3. Validação

- [x] 3.1 Adicionar regressões backend para membros compartilhados, item removido, offsets e exports TXT sem PII; verificar com `pytest -q tests/test_derived_galleries.py -k statistics`. Evidência: 2 testes aprovados, 82 deselecionados e somente warnings de depreciação do FastAPI.
- [x] 3.2 Adicionar regressões frontend para payload paginado, controles, retry e ausência de estado falso de zero; verificar com `npm test -- --pool=threads --maxWorkers=1 app/admin/statistics/page.test.tsx`. Evidência: 3 testes aprovados.
- [x] 3.3 Executar testes direcionados, Ruff, lint, typecheck, build e validação estrita da change; registrar evidências neste arquivo e confirmar `git diff --check` sem erro. Evidência: Ruff aprovado; Vitest direcionado 3/3; pytest direcionado 2/2; `eslint .` 0 erros e 25 warnings preexistentes; TypeScript e `next build` aprovados; OpenSpec estrito aprovado; `git diff --check` sem erro.

## Evidência de integração

- A página mantém os filtros durante retry, pagina compradas e selecionadas separadamente e continua usando links TXT sem offsets.
- O backend mantém `purchased_count` e `selected_not_purchased_count` para compatibilidade e acrescenta totais explícitos.
- Nenhuma migration, configuração, segredo, deploy ou dado de homologação foi alterado.
