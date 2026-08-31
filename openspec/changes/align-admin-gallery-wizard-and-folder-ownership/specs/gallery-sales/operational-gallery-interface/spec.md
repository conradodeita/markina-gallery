## MODIFIED Requirements

> **Supersession:** a hierarquia e o editor de cinco etapas definidos abaixo permanecem válidos. Terminologia, modos de acesso, navegação simultânea pela Galeria pública autorizada e privada, derivação sob demanda e exclusão integral acompanhável passam a ser regidos por `improve-gallery-and-client-data-lifecycle`; este delta SHALL NOT ser reaplicado para restaurar comportamento incompatível.

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface orientada por galerias para criar e operar clientes, galerias-mãe não listadas, galerias privadas derivadas, pastas e JPEGs. A criação e a edição de uma galeria-mãe SHALL seguir as etapas Ajustes, Vendas, Detalhes, Imagens e Clientes, preservando o contexto da galeria durante todo o fluxo. A interface SHALL apresentar criação, edição, preparação e liberação com clareza, sem expor conteúdo antes da autenticação, autorização e liberação aplicáveis.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo inicia a criação ou edição de uma galeria-mãe
- **THEN** a interface apresenta as cinco etapas na ordem definida, mantém a galeria selecionada como contexto e informa o estado de conclusão retornado pelo backend

#### Scenario: Segunda responsável

- **WHEN** o fotógrafo vincula uma nova responsável a fotos já disponibilizadas para outra responsável
- **THEN** o sistema cria ou vincula uma galeria privada independente para a nova responsável sem alterar seleção, prazo, pedido ou histórico da primeira

#### Scenario: Pasta em preparação

- **WHEN** o fotógrafo abre uma pasta ainda não liberada
- **THEN** ele vê os JPEGs, o estado de processamento e as ações de edição ou liberação disponíveis somente para ele

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

#### Scenario: Detalhes configuráveis

- **WHEN** o fotógrafo acessa a etapa Detalhes
- **THEN** a interface apresenta e persiste capa, título e organização suportados para aquela galeria, sem misturar upload, marca-d’água global ou opções simuladas

#### Scenario: Operação legada fora da navegação

- **WHEN** o fotógrafo usa a navegação administrativa
- **THEN** a interface apresenta Galerias como entrada operacional e não apresenta Operação como destino ativo, preservando somente o redirecionamento de URLs antigas

#### Scenario: Clientes agrupados por intenção

- **WHEN** o fotógrafo abre a etapa Clientes
- **THEN** responsáveis vinculados, busca de cadastro existente e novo cadastro aparecem em blocos distintos, responsivos e com ações textuais visíveis

#### Scenario: Legibilidade das ações administrativas

- **WHEN** um botão está disponível, em foco, sob ponteiro ou desabilitado
- **THEN** seu texto permanece visível, seu estado é distinguível e o agrupamento visual deixa claro qual bloco será afetado
