# Spec Delta

## MODIFIED Requirements

### Requirement: Persistência do histórico privado

O sistema SHALL manter uma biblioteca individual para a cliente autorizada, com no máximo uma entrada operacional por galeria, suas pastas comuns e atribuídas, seleções, pedidos e entregas. A interface SHALL identificar fotos já compradas e preservar o histórico permitido após a expiração da seleção. A limpeza pontual de dados de teste de homologação segue o requisito próprio de operação.

#### Scenario: Biblioteca vazia

- **WHEN** a cliente autenticada não possui vínculo ativo nem entrega histórica
- **THEN** a interface mostra estado vazio sem sugerir ou revelar galerias de terceiros

#### Scenario: Nova pasta liberada

- **WHEN** o fotógrafo libera uma nova pasta para a cliente
- **THEN** a mesma galeria apresenta a nova rodada separadamente das fotos já revisadas

#### Scenario: Histórico após expiração

- **WHEN** o prazo de seleção da cliente expira
- **THEN** ela continua acessando seus pedidos, entregas e identificação de fotos compradas, sem selecionar fora das regras de reativação

### Requirement: Interface da cliente orientada pelo backend

O sistema SHALL renderizar biblioteca, pastas, público, permissões, prazo, interações, estados das fotos e histórico individual a partir de respostas autorizadas do backend. O frontend SHALL NOT inferir vínculo por link, telefone informado ou estado local.

#### Scenario: Permissão alterada

- **WHEN** o fotógrafo altera vínculo, prazo ou público de uma pasta
- **THEN** a cliente vê o estado autorizado atual, sem o frontend preservar acesso anterior

#### Scenario: Navegação sem Minha galeria

- **WHEN** uma cliente autenticada acessa sua galeria canônica
- **THEN** a Coleção oferece seleção, favoritos, comentários e pedido de novo prazo; o Carrinho oferece revisão e PIX; Compras oferece pedidos, estados de pagamento e entregas, sem botão ou página operacional “Minha galeria”

#### Scenario: Link legado da galeria privada

- **WHEN** uma cliente abre um link antigo de “Minha galeria”
- **THEN** o sistema verifica autenticação e vínculo antes de redirecionar à Coleção ou a Compras conforme o contexto, sem revelar dados de outra cliente

#### Scenario: Tentativa de criar galeria ou link privado novo

- **WHEN** uma chamada administrativa antiga tenta criar uma galeria derivada, emitir ou rotacionar seu link privado
- **THEN** o backend recusa a operação sem gravar a derivada ou capacidade nova; o vínculo simples da cliente com a galeria pública continua disponível

#### Scenario: Exportação individual após a unificação

- **WHEN** o fotógrafo exporta a seleção ou as compras de uma cliente no card da galeria canônica
- **THEN** o arquivo contém somente dados daquela cliente, as fotos selecionadas seguem o público atual e as compras confirmadas usam seus snapshots históricos, inclusive as legadas permitidas

#### Scenario: Galeria de outra responsável

- **WHEN** uma cliente conhece URL ou identificador de foto em pasta restrita atribuída a outra
- **THEN** a interface recebe acesso negado sem exibir metadados, foto, interações ou pedidos alheios
