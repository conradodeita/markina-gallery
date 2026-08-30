## Purpose

Definir galerias privadas derivadas pertencentes a uma única responsável, que reutilizam fotos autorizadas de um acervo-fonte sem misturar seleção, compras ou histórico entre pessoas.

## ADDED Requirements

### Requirement: Propriedade exclusiva da galeria privada derivada
O sistema SHALL atribuir cada galeria privada derivada a exatamente uma cliente/responsável. Seleção, favoritos, comentários, visualizações, pedidos, pagamentos, prazo e histórico dessa galeria SHALL pertencer apenas à sua proprietária.

#### Scenario: Responsáveis do mesmo evento
- **WHEN** mãe e pai recebem galerias privadas derivadas do mesmo acervo-fonte
- **THEN** cada um acessa somente a sua galeria, com seleção, carrinho, pedido e histórico independentes

#### Scenario: Tentativa de acesso cruzado
- **WHEN** uma cliente tenta acessar a galeria privada derivada de outra cliente
- **THEN** o sistema nega o acesso sem revelar a existência, fotos ou interações da galeria

### Requirement: Clonagem privada sem duplicação de mídia
O sistema SHALL permitir ao fotógrafo criar uma nova galeria privada derivada para outra cliente a partir de um acervo-fonte ou de uma galeria derivada existente, preservando referências às fotos autorizadas sem criar uma segunda cópia de JPEG, prévia ou original.

#### Scenario: Segunda responsável recebe acesso
- **WHEN** o fotógrafo cria uma galeria para o pai a partir das fotos já disponíveis para a mãe
- **THEN** o pai recebe uma nova galeria privada com regras iniciais configuráveis e histórico vazio, enquanto a galeria da mãe permanece inalterada

#### Scenario: Foto vendida a mais de uma pessoa
- **WHEN** a mesma foto é confirmada em pedidos de responsáveis diferentes
- **THEN** cada pedido mantém seu próprio registro comercial e o fotógrafo consegue identificar que a foto já foi vendida sem revelar compradores entre clientes

### Requirement: Entrada por link não listado e vínculo individual
O sistema SHALL tratar um link de galeria-fonte como não listado e insuficiente para conceder acesso a fotografias. O visitante SHALL informar nome e telefone, concluir OTP e ter uma relação individual autorizada antes de visualizar conteúdo privado.

#### Scenario: Cliente entra pelo link compartilhado
- **WHEN** uma pessoa abre um link não listado e conclui o OTP com sucesso
- **THEN** o sistema registra o vínculo da pessoa com a galeria-fonte e encaminha apenas para uma galeria privada autorizada ou para um estado de aguardando aprovação

#### Scenario: Evento coletivo protegido
- **WHEN** o acervo-fonte representa evento coletivo protegido
- **THEN** o sistema não apresenta grade coletiva após o OTP e exige criação ou aprovação de resultado privado antes de exibir fotografias

### Requirement: Continuidade segura na troca de telefone
O sistema SHALL permitir ao fotógrafo registrar um novo telefone verificado para a mesma cliente sem transferir a propriedade de galerias ou pedidos a outra pessoa, preservando o telefone e o nome históricos nos registros comerciais já concluídos.

#### Scenario: Troca de número da mesma cliente
- **WHEN** o fotógrafo confirma a troca de telefone de uma cliente existente
- **THEN** o novo telefone autenticado recupera a biblioteca e o histórico da mesma cliente, enquanto pedidos concluídos preservam os dados históricos necessários à auditoria

### Requirement: Estados privados de descoberta e compra
O sistema SHALL apresentar o estado de cada foto exclusivamente no contexto da proprietária: `nova`, `visualizada mas não comprada` ou `já comprada`. A visualização SHALL ser registrada somente quando a cliente abre a foto ampliada, não pelo carregamento de miniatura.

#### Scenario: Cliente revisita o evento
- **WHEN** uma cliente abre novamente uma galeria privada com fotos antigas e novas
- **THEN** a interface diferencia as fotos já compradas, as ampliadas sem compra e as novas para aquela cliente
