## Context

`GET /admin/parent-galleries/{parent_gallery_id}/clients/{client_id}/selection/export.html` já gera, em memória, um HTML autônomo com as fotos compradas da cliente na galeria pública, embutindo prévias históricas ou administrativas disponíveis. A ação existente fica no acervo da cliente em “Galerias”. Em “Vendas e pagamentos”, cada pedido contém a galeria pública e o card renderiza `PaymentActions` para confirmar ou corrigir sua situação financeira.

## Goals / Non-Goals

**Goals:** colocar o acesso ao HTML junto às ações financeiras após confirmação; reutilizar o endpoint e os mesmos critérios de autorização e conteúdo; compor um nome de arquivo com o nome da cliente sem permitir injeção de cabeçalhos ou caminhos.

**Non-Goals:** gerar um HTML diferente por pedido; incluir seleções não compradas; baixar originais; persistir cópias do HTML; alterar critérios de confirmação ou correção financeira; permitir exportação sem compra confirmada.

## Decisions

1. **Escopo do relatório.** Manter o escopo atual do export: todas as compras confirmadas da mesma cliente naquela galeria derivada. A ação aparece no card de pedido após a confirmação financeira; pedidos não confirmados não oferecem o download. Isso preserva a semântica do botão existente mesmo quando a cliente possui mais de um pedido confirmado na galeria.

2. **Reutilização do endpoint.** O frontend monta o mesmo URL administrativo do acervo, usando o ID da galeria pública do pedido e o ID da cliente do grupo. A proteção `require_admin`, validação de vínculo e filtro de pedidos confirmados permanecem no servidor. Não criar endpoint ou consulta por card.

3. **Nome do arquivo.** O backend deriva o nome da cliente autenticada/responsável pelo pedido, normaliza-o para um único componente de nome e remove separadores de caminho, caracteres de controle e caracteres proibidos por sistemas de arquivos. O cabeçalho `Content-Disposition` fornece um fallback ASCII e o nome UTF-8 via parâmetro codificado conforme RFC 5987; sempre mantém extensão `.html`. Título e conteúdo do documento seguem escapados como hoje.

4. **Pedido sem exportável.** O link aparece somente quando o pedido está confirmado e os ativos/relação de galeria necessários para a rota estiverem disponíveis conforme a projeção. A resposta existente continua recusando relatório sem compras, sem gerar arquivo vazio.

## Risks / Trade-offs

- O relatório mantém o comportamento agregado da galeria, então pode incluir fotos de outros pedidos confirmados da mesma cliente e galeria. Isso é intencional para preservar o export existente.
- Nomes podem conter acentos e pontuação; o fallback ASCII mantém compatibilidade com clientes HTTP antigos, enquanto `filename*` preserva o nome legível.

## Migration Plan

Sem migration. Atualizar contrato OpenSpec e interface/backend, executar testes focados do export e do card e validar a change. Durante integração com `develop`, manter a experiência recente de pagamento por cartão e usar o endpoint canônico já acionado pelo acervo.

## Open Questions

Nenhuma. A semântica agregada por cliente e galeria foi escolhida para corresponder ao botão de exportação existente.
