# Spec Delta

## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface para criar e operar uma galeria por evento, seus clientes, pastas e JPEGs, com público comum ou restrito por pasta. A interface SHALL apresentar fluxo claro de criação, edição, preparação e liberação, sem criar galeria derivada nem expor acervo antes da autorização e liberação aplicáveis. Na etapa Imagens, cada pasta restrita SHALL ser identificada no próprio título pelos nomes das clientes atribuídas retornados pelo backend, mantendo o restante do card e o estado da pasta juntos; a etapa SHALL NOT adicionar uma seção separada para listar pastas de galerias privadas derivadas.

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

#### Scenario: Identificação no título da pasta restrita

- **WHEN** o fotógrafo consulta uma pasta restrita atribuída a uma ou mais clientes na etapa Imagens
- **THEN** o título do card exibe o nome da pasta seguido pelos nomes das clientes atribuídas, sem uma seção separada de galerias privadas derivadas

#### Scenario: Pasta restrita sem atribuições retornadas

- **WHEN** a etapa Imagens consulta uma pasta restrita sem nomes de clientes atribuídas
- **THEN** o título continua exibindo o nome da pasta sem inventar responsável ou ocultar o card

#### Scenario: Upload de pasta restrita na etapa Imagens

- **WHEN** o fotógrafo envia um ou mais arquivos para uma pasta restrita pela etapa Imagens
- **THEN** a interface associa os arquivos aceitos a um lote de upload e fecha o lote após as tentativas, inclusive quando algum arquivo falha, para que o processamento existente possa preparar o aviso quando os resultados elegíveis estiverem disponíveis

#### Scenario: Upload de pasta comum na etapa Imagens

- **WHEN** o fotógrafo envia arquivos para uma pasta comum pela etapa Imagens
- **THEN** o upload segue sem lote de aviso de pasta restrita e conserva o comportamento atual de preparação automática
