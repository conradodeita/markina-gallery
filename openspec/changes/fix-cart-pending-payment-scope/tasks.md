# Tasks

- [x] 1. Registrar regressões reproduzíveis de seleção nova versus compra incerta e delimitar proteção existente.
- [x] 2. Corrigir projeção e UI sem alterar tentativas/snapshots nem permitir fotos reservadas em nova cobrança.
- [x] 3. Validar testes locais focados, isolamento, lint, typecheck/build e revisão proporcional do diff; registrar evidência.
- [x] 4. Revisar diff e preparar PR draft com gates de CI final e limites explícitos; nenhuma publicação corretiva sem autorização específica.

## Evidence

Regressão antes da correção: dois casos backend (tentativa unknown/accepted) falharam por devolver card_payment antigo para foto nova; caso de foto reservada já foi recusado. Após correção inicial: 3 aprovados em SQLite (35,76s). Repetição final em PostgreSQL: 67 aprovados (375,15s), incluindo checkout, concorrência, várias pendências e comércio multi-tenant. UI carrinho/compras: 34 aprovados. Ruff, OpenSpec estrito, TypeScript e build aprovados; ESLint sem erros, com dois avisos preexistentes. Detalhes e limites em validation.md. PR draft #263 criado após revisão do diff; o container de teste foi encerrado/removido. Nenhum provedor real foi chamado e nenhuma compra real foi alterada.

## Gate final de entrega e publicação

CI completo do head é obrigatório antes de declarar validação final. Na preparação deste registro o CI estava em execução; resultado final, SHA e run SHALL ser registrados no corpo do [PR #263](https://github.com/conradodeita/markina-gallery/pull/263), sem tratar jobs pendentes como aprovação. As tasks concluídas acima registram implementação e preparação local, não aceite financeiro, revisão humana, merge ou publicação. Não há autorização de deploy desta correção nem de recuperação das compras reais.
