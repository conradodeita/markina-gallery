## ADDED Requirements

### Requirement: Carrinho persistente e editável até a comunicação

O sistema SHALL manter um único carrinho em rascunho por cliente e Galeria pública, incluindo seleções feitas na grade completa, na galeria privada autorizada ou nos resultados faciais da mesma galeria. Acionar `Prosseguir` SHALL abrir ou atualizar a conferência sem remover a seleção nem congelar seu conteúdo; enquanto o pagamento não tiver sido comunicado e o prazo permitir, a cliente SHALL poder retomar, adicionar ou remover fotos.

#### Scenario: Cliente retorna antes de comunicar o pagamento

- **WHEN** a cliente seleciona fotos, abre a conferência e encerra a página sem informar o pagamento
- **THEN** um novo acesso autenticado restaura as mesmas fotos, quantidade, cotação e ação para continuar o carrinho

#### Scenario: Cliente altera a seleção depois de prosseguir

- **WHEN** a cliente volta da conferência para a galeria e adiciona ou remove uma foto antes de comunicar o pagamento
- **THEN** o backend atualiza o mesmo rascunho e recalcula quantidade, parcelas e total sem criar outro pedido comercial

#### Scenario: Seleções em pastas diferentes

- **WHEN** a cliente escolhe fotos de várias pastas da mesma Galeria pública
- **THEN** as fotos integram um único carrinho e uma única cotação daquela galeria

#### Scenario: Cliente usa galerias diferentes

- **WHEN** a mesma cliente seleciona fotos em duas Galerias públicas
- **THEN** o sistema mantém carrinhos independentes e não combina fotos, valores, prazos ou pedidos

### Requirement: Congelamento atômico ao informar pagamento

O sistema SHALL congelar fotos, quantidade, valores, parcelas, regras comerciais, configuração PIX e texto de venda somente quando a cliente acionar `Informar pagamento`. A comunicação SHALL validar e registrar o retrato corrente do carrinho na mesma transação, impedir alterações posteriores naquele pedido e ser idempotente diante de repetição ou concorrência.

#### Scenario: Cliente informa o pagamento

- **WHEN** a cliente confirma `Informar pagamento` para um carrinho válido e ainda aberto
- **THEN** o backend cria ou finaliza um único pedido congelado com as fotos e valores exibidos e registra uma única comunicação pendente de revisão

#### Scenario: Clique ou requisição repetida

- **WHEN** a mesma comunicação é enviada mais de uma vez com a mesma chave ou concorre com outra tentativa
- **THEN** o sistema devolve o mesmo pedido congelado sem duplicar itens, comunicação ou valor

#### Scenario: Alteração concorrente da seleção

- **WHEN** uma inclusão ou remoção concorre com a comunicação do pagamento
- **THEN** o backend serializa as operações e congela um conjunto coerente, devolvendo à cliente o estado autoritativo resultante

#### Scenario: Nova compra após comunicação

- **WHEN** a cliente de um pedido congelado escolhe outras fotos elegíveis durante o prazo da galeria
- **THEN** essas escolhas iniciam um novo carrinho e futuro pedido complementar sem alterar o pedido congelado

### Requirement: Compatibilidade dos pedidos pendentes existentes

O sistema SHALL preservar pedidos pendentes criados antes desta mudança como snapshots congelados, sem recriar seleções, combinar pedidos ou alterar valores. A cliente SHALL poder consultar suas fotos e comunicar o pagamento conforme o estado já persistido.

#### Scenario: Pedido legado sem comunicação

- **WHEN** o deploy encontra pedido pendente existente cuja seleção já foi consumida pelo checkout anterior
- **THEN** o pedido permanece congelado e retomável com seus itens e valores originais, sem ser convertido em carrinho editável
