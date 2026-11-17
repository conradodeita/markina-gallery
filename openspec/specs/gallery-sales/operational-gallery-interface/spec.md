# operational-gallery-interface Specification

## Purpose

Permitir ao fotógrafo operar a galeria única, seus clientes e pastas pela interface, sem expor acervos não autorizados ou exigir chamadas técnicas.

## Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface para criar e operar uma galeria por evento, seus clientes, pastas e JPEGs, com público comum ou restrito por pasta. A interface SHALL apresentar fluxo claro de criação, edição, preparação e liberação, sem criar galeria derivada nem expor acervo antes da autorização e liberação aplicáveis.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui o fluxo com dados válidos
- **THEN** o sistema cria somente a galeria e suas pastas necessárias, com confirmação ou erro acessível, sem derivada automática

#### Scenario: Segunda responsável

- **WHEN** o fotógrafo vincula outra responsável à mesma galeria
- **THEN** a responsável vê pastas comuns e as atribuídas a ela, com seleção, prazo, pedidos e histórico independentes

#### Scenario: Pasta em preparação

- **WHEN** o fotógrafo abre uma pasta ainda não liberada
- **THEN** ele vê JPEGs, processamento, público pretendido e ações administrativas; nenhuma cliente vê a pasta

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a galeria
- **THEN** não vê controles administrativos nem pastas ou fotos fora de sua autorização

### Requirement: Estados operacionais claros

O sistema SHALL apresentar estados de carregamento, vazio, erro, preparação, progresso, sucesso, bloqueio e expiração nas telas administrativas e da cliente, com linguagem compreensível e ação de recuperação quando aplicável. A página Estatísticas SHALL apresentar estados distintos para ausência de vendas, seleções sem compra, dados indisponíveis e falha de consulta, sem substituir falhas ou dados não instrumentados por zero, e preservar os filtros durante a recuperação.

#### Scenario: Falha ao consultar estatísticas

- **WHEN** a API de Estatísticas falha
- **THEN** a página informa erro recuperável, preserva filtros e não exibe receita zero como se fosse resultado real

#### Scenario: Importação em processamento

- **WHEN** um JPEG foi aceito e seus derivados ainda estão sendo preparados
- **THEN** o fotógrafo vê o estado pendente sem receber URL do original

#### Scenario: Liberação concluída

- **WHEN** o fotógrafo conclui a liberação de uma pasta
- **THEN** a interface confirma o público efetivo retornado pelo backend e as clientes alcançadas, sem sugerir atualização de galerias derivadas

#### Scenario: Galeria sem prazo de seleção configurado

- **WHEN** a galeria/cliente não tem prazo de seleção persistido ou ele ainda não expirou
- **THEN** suas seleções não são classificadas como abandonadas e nenhum prazo ou valor potencial é inventado

### Requirement: Interface orientada pelo backend

APIs autenticadas do backend SHALL ser a fonte de dados, permissões, disponibilidade e resultados administrativos. Filtros, tabelas e indicadores SHALL compartilhar escopo; valores consolidados SHALL abrir registros detalhados. A interface SHALL NOT autorizar CSV só ocultando botão nem simular permissões, registros, progresso ou liberações no browser.

#### Scenario: Filtros combinados

- **WHEN** o fotógrafo combina período, galeria, pasta, cliente ou forma de pagamento
- **THEN** indicadores, detalhamento HTML e subtotais refletem exatamente o mesmo conjunto autorizado de itens e pedidos

#### Scenario: Acesso a exportação CSV

- **WHEN** a interface apresenta a ação de CSV
- **THEN** o backend ainda revalida a autorização do proprietário para a URL direta e a ação

#### Scenario: Estado administrativo

- **WHEN** o fotógrafo abre ou altera uma tela operacional
- **THEN** a interface consulta o backend e apresenta o estado retornado, sem criar autorização ou registros simulados no browser

#### Scenario: Consulta por responsável

- **WHEN** o fotógrafo busca por nome ou telefone na ficha de uma galeria-fonte
- **THEN** o sistema retorna apenas os vínculos e estados autorizados da consulta e permite abrir a ficha individual da seleção

### Requirement: Exclusão segura de galeria privada

O sistema SHALL permitir exclusão operacional de galeria ou pasta somente se os vínculos, mídias e registros comerciais protegidos permitirem. Uma compra confirmada SHALL bloquear remoção que apagaria o histórico; bloqueio ou congelamento de acesso SHALL permanecer disponível conforme a regra comercial.

#### Scenario: Histórico de compra preservado

- **WHEN** o fotógrafo tenta excluir uma galeria ou pasta com foto de pedido confirmado
- **THEN** o backend recusa a exclusão e preserva o pedido e seus snapshots

### Requirement: Acervo da cliente no card da Galeria pública

Cada card de cliente SHALL ter seção recolhida `Acervo da cliente` para pastas restritas, upload JPEG e atribuições controladas pelo backend. Abrir/recolher SHALL alterar somente a apresentação. A pasta nasce atribuída à cliente do card e permanece única ao ser compartilhada; pastas comuns ficam em Imagens. A interface SHALL NOT criar, clonar ou abrir galeria privada derivada.

#### Scenario: Fotógrafo abre o card

- **WHEN** o fotógrafo expande `Acervo da cliente` no card de uma cliente
- **THEN** vê o acervo, pode criar pasta restrita e enviar fotos naquele contexto, sem navegar para uma galeria privada

#### Scenario: Pasta compartilhada por dois cards

- **WHEN** o fotógrafo adiciona outra cliente à pasta restrita criada em um card
- **THEN** ambos os cards mostram a mesma pasta, sem duplicar fotos ou reiniciar seleções e pedidos individuais

### Requirement: Navegação global de clientes

O sistema SHALL apresentar `Clientes` como destino próprio da navegação administrativa, sem depender do contexto ou da existência de uma galeria. A etapa Clientes de uma Galeria pública SHALL reutilizar o mesmo cadastro global e acrescentar somente ações e estados específicos do vínculo atual.

#### Scenario: Diretório e etapa usam a mesma identidade

- **WHEN** o fotógrafo edita uma cliente no diretório global e depois abre a etapa 05
- **THEN** a etapa apresenta o mesmo cadastro atualizado, inclusive quando já vinculado, sem criar ou manter uma cópia local

### Requirement: PIX global na etapa Vendas

O sistema SHALL remover da etapa Vendas a edição de chave, BR Code, recebedor, cidade e instruções PIX por galeria. A etapa SHALL consultar o contrato global e apresentar seu estado, prévia e destino de correção antes de salvar e avançar.

#### Scenario: Fotógrafo avança na etapa 02

- **WHEN** o fotógrafo salva preço e demais regras comerciais da galeria
- **THEN** o sistema persiste somente esses dados por galeria e mantém a configuração PIX sob o contrato global

### Requirement: Cards de clientes vinculadas por atividade

O sistema SHALL apresentar os cards de clientes vinculadas a uma Galeria pública em uma única coluna e ordená-los pela atividade de acesso mais recente primeiro. A ordem SHALL usar a última visualização de prévia protegida registrada para a Galeria pública ou galeria privada correspondente e, quando inexistente, a data de criação do vínculo. O menu recolhível e os demais controles existentes SHALL permanecer disponíveis.

#### Scenario: Cliente retorna à galeria

- **WHEN** uma cliente visualiza uma prévia protegida depois das demais clientes
- **THEN** seu card aparece no topo após a próxima consulta à lista

#### Scenario: Cliente ainda não abriu prévias

- **WHEN** não há visualização protegida registrada para uma cliente vinculada
- **THEN** o sistema ordena seu card pela data de criação do vínculo, mantendo clientes sem data no final

#### Scenario: Lista em telas largas

- **WHEN** o fotógrafo consulta clientes vinculadas em uma tela larga
- **THEN** cada card ocupa uma linha e mantém o menu recolhível e os demais controles

### Requirement: Cobrança obrigatória com recebimento disponível

O sistema SHALL exigir ao menos um meio utilizável da conta autenticada ao salvar a etapa 2 com `Pagamento obrigatório?` marcado ou disponibilizar essa galeria às clientes. PIX válido SHALL ser padrão; cartão SHALL contar somente com configuração pronta e habilitação individual. Ausência de meios SHALL rejeitar a operação sem alteração parcial, com orientação para Configurações. Criar rascunho SHALL continuar possível antes de configurar recebimento.

#### Scenario: Cobrança obrigatória sem recebimento

- **WHEN** o fotógrafo salva a etapa 2 paga sem PIX utilizável nem cartão habilitado/pronto
- **THEN** UI e API recusam a configuração e orientam configurar recebimento ou desmarcar cobrança obrigatória
- **AND** preço, modo e demais campos anteriores permanecem inalterados

#### Scenario: Recebimento pertence a outro fotógrafo

- **WHEN** somente outra conta possui PIX ou cartão disponível
- **THEN** a configuração paga e a disponibilização não usam esse meio para satisfazer a exigência da conta atual

#### Scenario: Reativação de galeria já publicada

- **WHEN** o fotógrafo tenta reativar uma galeria paga com pastas já liberadas e sem meio utilizável
- **THEN** a API recusa a reativação sem alterar o estado inativo, até configurar recebimento

#### Scenario: PIX e cartão disponíveis

- **WHEN** a cliente inicia revisão paga de uma conta com ambos os meios utilizáveis
- **THEN** PIX inicia selecionado e cartão pode ser escolhido explicitamente

#### Scenario: Cartão utilizável sem PIX cadastrado

- **WHEN** a conta nunca configurou PIX e possui cartão pronto e habilitado
- **THEN** cartão satisfaz a exigência de pelo menos um meio e sua preparação não depende de um PIX inexistente

### Requirement: Preservação do último meio de galeria paga

Alterações de configuração SHALL revalidar no servidor se deixariam galeria disponibilizada com cobrança obrigatória sem qualquer meio utilizável. Nesse caso SHALL ser recusadas sem alteração parcial e orientar configurar outro meio ou mudar explicitamente a jornada das galerias afetadas. Pedidos e links já emitidos SHALL manter snapshots e reservas conforme o contrato existente.

#### Scenario: Desligar cartão com PIX disponível

- **WHEN** o fotógrafo desliga a oferta de cartão e conserva PIX utilizável
- **THEN** novos pedidos dessa conta continuam pagando por PIX e outras contas permanecem independentes

#### Scenario: Retirar último meio utilizável

- **WHEN** alteração InfinitePay retiraria o único meio de uma galeria paga disponibilizada
- **THEN** a alteração é rejeitada e a configuração anterior permanece

### Requirement: Jornada sem cobrança independente do recebimento

Com `Pagamento obrigatório?` desmarcado, o sistema SHALL permitir salvar regras e finalizar seleção sem configurar PIX/cartão. A revisão SHALL apresentar `Finalizar seleção` e ocultar meios, preços e totais daquele grupo. Finalização SHALL preservar identidade, autorização, revisão e idempotência existentes, sem gerar cobrança, receita ou aviso financeiro. Carrinhos mistos SHALL cobrar somente grupos pagos.

#### Scenario: Galeria somente para seleção

- **WHEN** a cliente revisa somente fotos de galerias sem cobrança e a conta não tem recebimento configurado
- **THEN** pode finalizar a seleção sem etapa PIX ou InfinitePay e sem preço ou total

#### Scenario: Carrinho com dois modos

- **WHEN** a cliente reúne uma galeria paga e outra sem cobrança
- **THEN** o grupo sem cobrança mantém finalização independente, mesmo se o grupo pago tiver erro de configuração

### Requirement: Busca de cliente por nome ou telefone em Vendas e pagamentos

A área Vendas e pagamentos SHALL manter um único filtro de cliente que localize registros por nome ou telefone cadastrado e ofereça sugestões de clientes correspondentes durante a digitação.

#### Scenario: Sugestões de nome

- **WHEN** o fotógrafo digita parte do nome de uma cliente no filtro existente
- **THEN** a área sugere nomes correspondentes e permite escolher uma cliente sem criar outro campo de busca

#### Scenario: Seleção exata ou busca livre

- **WHEN** o fotógrafo escolhe uma sugestão ou aplica texto parcial de nome/telefone
- **THEN** a área filtra seleções abertas e pedidos pela identidade escolhida ou pelo texto informado, respectivamente

#### Scenario: Paginação com busca

- **WHEN** a busca por cliente possui resultados em mais de uma página
- **THEN** carregar clientes adicionais preserva o mesmo critério de nome ou telefone

### Requirement: Filtros de vendas visíveis no topo durante a rolagem

A área Vendas e pagamentos SHALL posicionar o filtro existente antes dos resumos e listas operacionais e mantê-lo acessível abaixo da navegação administrativa durante a rolagem, sem cobrir conteúdo nem controles em telas pequenas.

#### Scenario: Consulta inicial

- **WHEN** o fotógrafo abre Vendas e pagamentos
- **THEN** encontra o filtro antes de Seleções em aberto, pedidos e demais cards operacionais

#### Scenario: Rolagem do painel

- **WHEN** o fotógrafo rola pelos cards e listas
- **THEN** o filtro permanece acessível no topo abaixo da navegação e não encobre os controles operacionais

### Requirement: Clientes com seleção atual na Visão geral

A Visão geral SHALL apresentar até cinco grupos de seleção atual do tenant autenticado, com cliente, Galeria pública, quantidade de fotos e o instante em que o carrinho atual começou. Os grupos SHALL ser ordenados pela atividade de seleção mais recente, e o card SHALL preservar os atalhos de galerias recentes.

#### Scenario: Cliente inicia uma seleção

- **WHEN** uma cliente autorizada seleciona fotos em uma Galeria pública
- **THEN** a próxima consulta da Visão geral pode apresentar o grupo dessa cliente, com a quantidade atual e o instante em que a primeira foto da seleção atual foi escolhida

#### Scenario: Remover a primeira foto escolhida

- **WHEN** a cliente remove a primeira foto que escolheu, mas mantém outras fotos no carrinho
- **THEN** o horário de início permanece o instante em que a seleção atual começou

#### Scenario: Ordenar atividade recente

- **WHEN** há mais de cinco grupos com fotos selecionadas
- **THEN** a Visão geral apresenta os cinco grupos com adição de foto mais recente, identificando o início de cada seleção atual

#### Scenario: Seleção de outro tenant

- **WHEN** uma cliente de outro tenant tem fotos selecionadas
- **THEN** a Visão geral atual não revela seu nome, galeria, quantidade ou horário

#### Scenario: Nenhum grupo atual

- **WHEN** nenhuma foto permanece selecionada em qualquer grupo do tenant
- **THEN** a interface apresenta um estado vazio sem inventar cliente ou atividade histórica

### Requirement: Horário sem registro do carrinho atual

Se o horário exato não estiver registrado, a interface SHALL mostrar `Horário não registrado` e não SHALL estimar o início pelas fotos que restaram.

#### Scenario: Carrinho sem início registrado

- **WHEN** há uma seleção atual sem horário exato registrado
- **THEN** a interface mantém cliente e galeria visíveis e informa `Horário não registrado`, sem estimar o início

### Requirement: Fuso horário visível do horário da seleção

O backend SHALL manter e retornar o instante da seleção em UTC. Como não há fuso configurável por tenant, a Visão geral SHALL exibir a hora convertida para o fuso local do dispositivo e identificar essa regra na interface.

#### Scenario: Apresentar o horário registrado

- **WHEN** a Visão geral apresenta um início exato de seleção
- **THEN** a interface converte o instante UTC para o fuso do dispositivo e informa que os horários seguem esse fuso
