## ADDED Requirements

### Requirement: Identificação visual das pastas administrativas

O resumo administrativo SHALL chamar a lista comum de `Pastas Públicas`; no `Acervo da cliente`, a lista atribuída SHALL ser `Pastas restritas ao cliente`. Cada card SHALL exibir nome, contagem, estado e sua própria prévia protegida quando pronta. Prévia e texto, ou placeholder textual, SHALL compor ação única para abrir/recolher somente a pasta. Essa ação SHALL alterar apenas a apresentação, sem mudar público, configuração ou processamento.

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

O resumo da galeria SHALL filtrar somente os cards de clientes vinculadas por nome ou telefone, sem alterar dados ou contadores do backend; resultado vazio SHALL mostrar estado claro e permitir limpar o filtro para restaurar a lista. A busca geral da página `Galerias` SHALL continuar encontrando galerias por nome, evento ou cliente vinculada pelo modelo atual, limitando os resultados às galerias autorizadas do fotógrafo.

#### Scenario: Cliente vinculada encontrada no resumo

- **WHEN** o fotógrafo digita nome ou telefone de uma entre duas clientes vinculadas à galeria aberta
- **THEN** somente o card correspondente permanece visível, sem criar ou alterar vínculos

#### Scenario: Busca sem correspondência

- **WHEN** o termo não corresponde a nenhuma cliente daquela galeria
- **THEN** aparece uma mensagem de nenhum resultado e limpar o termo restaura todos os cards

#### Scenario: Busca geral por vínculo atual

- **WHEN** o fotógrafo pesquisa na página `Galerias` por cliente vinculada à galeria única sem derivada legada
- **THEN** a galeria correspondente aparece no resultado, sem expor clientes ou galerias fora do contexto administrativo
