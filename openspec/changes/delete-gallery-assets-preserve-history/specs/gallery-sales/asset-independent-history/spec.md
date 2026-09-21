## ADDED Requirements

### Requirement: Histórico independente do acervo
O sistema SHALL preservar os movimentos existentes da cliente e snapshots textuais de pedidos antes da exclusão de galeria, pasta ou foto, incluindo nome da foto, galeria/pasta, identidade autorizada, datas, valores e estados comerciais. A exclusão SHALL NOT cancelar, confirmar, recusar ou comunicar pagamento.

#### Scenario: Seleção sem compra
- **WHEN** o fotógrafo exclui uma foto selecionada sem pedido
- **THEN** a seleção deixa o carrinho ativo e permanece identificável como seleção não comprada no histórico, com nome da foto e contexto
- **AND** nenhuma venda ou comunicação financeira é criada

#### Scenario: Pagamento comunicado ou confirmado
- **WHEN** o fotógrafo exclui acervo associado a pagamento comunicado ou confirmado
- **THEN** valores, itens, nomes e estados permanecem consultáveis e as decisões administrativas continuam aplicáveis ao conjunto original
- **AND** arquivos e prévias do acervo excluído deixam de ser servidos

### Requirement: Revisão indisponível preservada
O sistema SHALL preservar pedidos e composição de PIX iniciados afetados pela exclusão e impedir sua sincronização ou nova cobrança automática; uma nova seleção SHALL permitir outro carrinho sem apagar o histórico anterior.

#### Scenario: PIX único com acervo removido
- **WHEN** parte de um PIX ainda não comunicado é excluída
- **THEN** o histórico preserva o total e todos os itens anteriores, identifica indisponibilidade e não oferece cobrança parcial silenciosa
- **AND** um grupo já comunicado mantém sua decisão financeira atômica

### Requirement: Consulta autorizada sem imagens
Vendas e pagamentos SHALL apresentar movimentos e referências textuais removidos. A cliente SHALL acessar somente seus próprios registros; a ausência de imagem SHALL ser representada sem link quebrado nem restauração de acesso ao acervo.

#### Scenario: Outra identidade
- **WHEN** uma cliente consulta seu histórico após exclusão
- **THEN** recebe somente movimentos e pedidos da sua identidade, com nomes das fotos e indicação de acervo removido

### Requirement: Exclusão retomável e confinada
O sistema SHALL registrar progresso e falhas reais de limpeza e permitir retentativa idempotente, sem excluir caminhos externos ao storage nem recursos de outros projetos.

#### Scenario: Operação antiga falha
- **WHEN** o administrador retoma uma exclusão antiga que falhou após remover arquivos
- **THEN** o sistema preserva metadados disponíveis, recompõe o escopo autorizado e conclui a limpeza sem exigir mídia já ausente
- **AND** a publicação de código isoladamente não reinicia exclusões antigas
