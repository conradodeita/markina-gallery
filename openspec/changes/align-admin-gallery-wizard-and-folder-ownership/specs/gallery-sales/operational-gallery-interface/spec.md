## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface orientada por galerias para criar e operar clientes, galerias-mãe não listadas, galerias privadas derivadas, pastas e JPEGs. A criação e a edição de uma galeria-mãe SHALL seguir as etapas Ajustes, Vendas, Detalhes, Imagens e Clientes, preservando o contexto da galeria durante todo o fluxo. A interface SHALL apresentar criação, edição, preparação e liberação com clareza, sem expor conteúdo antes da autenticação, autorização e liberação aplicáveis.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo inicia a criação ou edição de uma galeria-mãe
- **THEN** a interface apresenta as cinco etapas na ordem definida, mantém a galeria selecionada como contexto e informa o estado de conclusão retornado pelo backend

#### Scenario: Pasta criada na etapa Imagens

- **WHEN** o fotógrafo acessa a etapa Imagens de uma galeria-mãe
- **THEN** ele pode listar e criar somente pastas pertencentes àquela galeria, carregar fotos em uma pasta em preparação e visualizar contagens e prévias autorizadas

#### Scenario: Ausência de criação global de pasta

- **WHEN** o fotógrafo navega pelo dashboard, pela lista de galerias ou por uma área global de mídia
- **THEN** a interface não oferece criação de pasta nem upload de foto sem antes selecionar ou criar a galeria-mãe proprietária

#### Scenario: Vendas ainda não configuradas

- **WHEN** uma capacidade comercial da etapa Vendas ainda não estiver implementada ou habilitada pelo backend
- **THEN** a interface apresenta o estado indisponível de forma explícita e não simula preço, pagamento ou configuração no navegador

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface por um link não listado
- **THEN** o sistema exige a autenticação aplicável e não revela controles administrativos nem fotos fora de sua galeria privada derivada e das pastas liberadas para ela

#### Scenario: Continuidade entre etapas

- **WHEN** o fotógrafo avança ou retorna entre etapas após salvar dados válidos
- **THEN** a interface recupera do backend os dados persistidos da mesma galeria e não cria galerias, pastas ou vínculos duplicados
