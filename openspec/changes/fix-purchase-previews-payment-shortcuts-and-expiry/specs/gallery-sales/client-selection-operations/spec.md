## ADDED Requirements

### Requirement: Ações financeiras contextuais nos cards de clientes

O sistema SHALL disponibilizar nos cards de clientes vinculados da Galeria pública e nos cards de membros da Galeria privada os atalhos `Confirmar pagamento`, `Pagamento não localizado` e `Corrigir confirmação`, conforme as capacidades devolvidas pelo backend para o pedido. As ações SHALL reutilizar as mesmas regras, confirmação explícita, auditoria e efeitos da área Vendas e pagamentos. Seleções e pedidos sem comunicação SHALL NOT oferecer confirmação financeira.

#### Scenario: Comunicação pendente de revisão
- **WHEN** o card possui um pedido com comunicação apta à decisão
- **THEN** o fotógrafo pode iniciar confirmação ou não localização diretamente no contexto desse cliente, conferindo identificação do pedido, galeria e valor antes de confirmar a ação

#### Scenario: Confirmação equivocada
- **WHEN** o fotógrafo utiliza `Corrigir confirmação` em pedido elegível e confirma a correção
- **THEN** o pedido retorna à revisão conforme a operação existente, sem nova mensagem WhatsApp ou push

#### Scenario: Cliente com múltiplos pedidos ou galerias
- **WHEN** existem vários pedidos para o mesmo cliente
- **THEN** cada ação identifica inequivocamente o pedido da galeria do card e não altera pedidos de outra galeria nem escolhe automaticamente um pedido ambíguo

#### Scenario: Nova compra não oculta pendências anteriores
- **WHEN** a cliente realiza compras sucessivas na mesma galeria
- **THEN** os pedidos com pagamento comunicado aguardando decisão aparecem primeiro, individualmente com quantidade, valor, data e identificação; nenhum pedido pendente é escondido pela compra mais recente
- **AND** novas seleções não alteram o conjunto congelado de uma compra anterior e uma ação nunca confirma outras compras da mesma cliente

#### Scenario: Estado alterado por outra sessão
- **WHEN** um pedido muda de estado depois que o card foi carregado
- **THEN** o backend revalida a decisão, a interface informa o conflito e atualiza os dados sem aplicar transição inválida

#### Scenario: Atualização e falha de mensagem
- **WHEN** uma decisão financeira é concluída, inclusive quando o envio de mensagem falha
- **THEN** o card atualiza status, totais, contagens e ações com o resultado financeiro persistido, mantendo a mensagem independente e evitando cliques duplicados durante a operação

### Requirement: Prazo efetivo visível para o fotógrafo

O sistema SHALL mostrar o prazo de seleção e seu tempo restante na ficha privada e nos cards de clientes vinculados que já possuam data efetiva. A duração padrão de uma pública sem data individual iniciada SHALL permanecer identificada como configuração, sem ser convertida em vencimento global fictício. Expiração de seleção SHALL NOT alterar o estado financeiro ou ocultar ações válidas de um pedido comunicado.

#### Scenario: Fotógrafo consulta prazo de uma cliente
- **WHEN** o fotógrafo abre o card ou ficha de uma privada com prazo efetivo
- **THEN** vê data/hora e tempo restante ou estado expirado da seleção daquela cliente, coerentes com a superfície cliente

#### Scenario: Clientes com datas diferentes
- **WHEN** privadas derivadas da mesma pública possuem datas efetivas diferentes
- **THEN** cada card exibe seu próprio prazo, sem usar um único contador para todas as clientes
