## Context

A API aceita no máximo 500 UUIDs em `PhotoBulkDeleteInput`, mas o editor envia toda a seleção em um único `DELETE`. A rota processa cada foto sequencialmente, aplica a política comercial comum, confirma a remoção e retorna listas de removidas, bloqueadas e ausentes. Consulte `proposal.md` para a motivação e o delta spec para o contrato observável.

## Goals / Non-Goals

**Goals:**

- Suportar seleções superiores a 2.000 fotos sem alterar o limite defensivo da API.
- Preservar uma única confirmação humana, processamento sequencial e resultado consolidado.
- Tornar falhas após progresso parcial explícitas e recuperáveis por nova tentativa.

**Non-Goals:**

- Não alterar a política comercial, as regras de retenção nem a autorização administrativa.
- Não transformar a exclusão de fotos em um job assíncrono nesta correção.
- Não excluir dados de homologação, executar deploy ou modificar o benchmark facial.

## Decisions

### Particionar no frontend em lotes sequenciais de 100 IDs

O editor deduplicará a seleção e enviará lotes sequenciais de até 100 IDs ao endpoint existente. O tamanho fica abaixo do máximo de 500 e reduz a duração e o impacto de cada requisição, importante porque a rota atual confirma e remove arquivos foto a foto.

Alternativas consideradas:

- Aumentar ou remover `max_length=500`: descartado porque amplia uma operação síncrona custosa e elimina uma proteção da API.
- Enviar lotes em paralelo: descartado porque aumenta contenção, dificulta ordenar efeitos parciais e pode sobrecarregar banco e armazenamento.
- Criar worker assíncrono: adequado para uma evolução maior, mas desproporcional ao defeito confirmado e exigiria novo contrato operacional.

### Consolidar resultados somente de respostas confirmadas

As listas `deleted_ids`, `blocked_ids` e `missing_ids` serão acumuladas entre lotes. A mensagem final exibirá os totais consolidados. Identificadores ausentes serão tratados como resultado idempotente e não como falha da operação inteira.

### Atualizar a pasta mesmo diante de falha intermediária

Se uma requisição falhar depois de lotes concluídos, o editor preservará a contagem de resultados confirmados, recarregará a pasta e informará que houve progresso parcial. A nova tentativa partirá do estado atual da interface, sem reenviar automaticamente lotes já concluídos.

## Risks / Trade-offs

- [Mais de vinte requisições em seleções superiores a 2.000 fotos] → lotes sequenciais limitam concorrência; a interface permanece ocupada até o término e consolida somente respostas confirmadas.
- [Falha de rede após o servidor concluir um lote, antes da resposta] → a recarga mostra o estado real e a repetição é segura porque itens já removidos deixam de aparecer.
- [Tempo total maior que uma única requisição] → aceito para reduzir risco de timeout e manter a API estável; o teste verificará a ordem sequencial.

## Migration Plan

1. Publicar somente o frontend corrigido junto ao SHA autorizado, sem migration ou mudança de configuração.
2. Validar em homologação com seleção superior a 2.000 fotos e conferir o total remanescente após a operação.
3. Em rollback, restaurar o frontend anterior; nenhum dado ou contrato da API precisa ser revertido.
