## Context
DELETE de pasta aceita somente preparação vazia. DELETE de foto já aplica commercial_removal, remove vínculos e registros faciais, confirma a transação e limpa caminhos confinados ao storage.

## Goals / Non-Goals
Habilitar remoção integral de uma pasta de conteúdo com a mesma política comercial; evitar remoção parcial quando uma foto bloquear a operação. Não remover pastas técnicas de capa nem dados de outras pastas.

## Decisions
- Bloquear a linha da pasta e suas fotos durante a operação; preservar validação de galeria mutável e escopo privado após exclusão da origem.
- Separar a remoção de registros de foto do commit e da limpeza física. A pasta aplica a política de todas as fotos primeiro, remove registros e pasta em uma transação e só então apaga arquivos seguros. Exclusão avulsa mantém seu contrato HTTP.
- Reutilizar a política comercial vigente, incluindo cancelamento de pendências e materialização de compras confirmadas, sem inventar uma nova regra de pagamento.
- Usar confirmação explícita no padrão atual das telas, impedir repetição durante a requisição e atualizar pastas/fotos após sucesso. A interface privada oferece a ação apenas para pastas próprias.

## Risks / Trade-offs
A operação usa o ciclo HTTP como a exclusão avulsa existente; grandes pastas podem exigir mais tempo. Não processa imagens novas. Falha física após commit segue a limpeza idempotente existente; nenhum arquivo é removido antes do commit. Requisições concorrentes de upload devem adquirir o bloqueio da pasta antes de inserir fotos.

## Validation
Testes de pasta vazia/liberada/com fotos, isolamento público/privado, rollback comercial, histórico, autenticação e confirmação na interface. Revisão de diff, lint, typecheck e build antes da entrega.
