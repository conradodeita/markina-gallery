## ADDED Requirements

### Requirement: Identificação visual das pastas administrativas

O resumo administrativo da galeria SHALL identificar a lista comum como `Pastas Públicas`. Dentro do `Acervo da cliente`, a lista de pastas atribuídas SHALL ser identificada como `Pastas restritas ao cliente`. Cada pasta restrita SHALL mostrar sua própria prévia protegida, quando pronta, junto do nome, contagem de fotos e estado; a prévia e o texto SHALL formar uma ação clicável única que abre e recolhe a pasta. A falta de prévia SHALL manter uma alternativa textual e a ação de abrir. Abrir ou recolher SHALL alterar somente a apresentação e SHALL NOT mudar configuração, público ou processamento.

#### Scenario: Duas pastas restritas com prévias

- **WHEN** o fotógrafo abre o Acervo de uma cliente com duas pastas que já possuem prévias
- **THEN** vê `Pastas restritas ao cliente` e uma capa distinta para cada pasta; clicar na capa abre apenas a pasta escolhida, preservando as demais fechadas

#### Scenario: Pasta vazia ou em processamento

- **WHEN** a pasta restrita ainda não possui prévia pronta
- **THEN** o card continua identificado por nome, contagem e estado e pode ser aberto sem fotografia

#### Scenario: Resumo da galeria

- **WHEN** o fotógrafo consulta o resumo da galeria
- **THEN** a lista de pastas comuns aparece sob o título `Pastas Públicas`, sem incluir pastas restritas de outras clientes

### Requirement: Busca de clientes no contexto da galeria

O resumo administrativo da galeria SHALL oferecer busca por nome ou telefone que filtre somente os cards de clientes vinculadas àquela galeria, preservando os dados e contadores gerais retornados pelo backend. Uma busca sem correspondência SHALL mostrar estado vazio claro e permitir retornar à lista completa. A busca geral da página `Galerias` SHALL continuar localizando galerias por nome, evento ou cliente vinculada pelo modelo atual; resultados SHALL continuar limitados às galerias existentes e autorizadas ao fotógrafo.

#### Scenario: Cliente vinculada encontrada no resumo

- **WHEN** o fotógrafo digita nome ou telefone de uma entre duas clientes vinculadas à galeria aberta
- **THEN** somente o card correspondente permanece visível, sem criar ou alterar vínculos

#### Scenario: Busca sem correspondência

- **WHEN** o termo não corresponde a nenhuma cliente daquela galeria
- **THEN** aparece uma mensagem de nenhum resultado e limpar o termo restaura todos os cards

#### Scenario: Busca geral por vínculo atual

- **WHEN** o fotógrafo pesquisa na página `Galerias` por cliente vinculada à galeria única sem derivada legada
- **THEN** a galeria correspondente aparece no resultado, sem expor clientes ou galerias fora do contexto administrativo
