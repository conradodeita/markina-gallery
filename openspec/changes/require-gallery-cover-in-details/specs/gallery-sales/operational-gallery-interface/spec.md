# Spec Delta

## ADDED Requirements

### Requirement: Capa obrigatória na etapa Detalhes

O sistema SHALL exigir capa explicitamente configurada da própria galeria e conta, com prévia pronta, para salvar a etapa Detalhes e concluir o fluxo guiado. Criação inicial, Ajustes e Vendas SHALL continuar disponíveis sem capa. O backend SHALL revalidar a prontidão no salvamento visual e fornecê-la à interface; somente informar um identificador não comprova a capa.

#### Scenario: Orientação concisa em Detalhes

- **WHEN** o fotógrafo abre Detalhes
- **THEN** a interface apresenta a obrigatoriedade e a prontidão da capa sem o parágrafo estático sobre JPEG horizontal, marca-d’água, grade ou carregamento de fotos das pastas

#### Scenario: Cadastro inicial sem capa

- **WHEN** o fotógrafo informa os dados iniciais e aciona Criar e continuar sem imagem
- **THEN** o sistema permite criar o contexto da galeria e preparar Ajustes/Vendas, mantendo Detalhes pendente até configurar uma capa pronta

#### Scenario: Tentativa de salvar Detalhes sem capa

- **WHEN** o fotógrafo tenta salvar ou avançar em Detalhes sem capa configurada válida
- **THEN** a interface orienta a definir a capa e o backend rejeita o salvamento visual sem gravar parcialmente os demais campos dessa requisição

#### Scenario: Capa preparando ou com falha

- **WHEN** a capa foi enviada mas a prévia ainda está preparando ou falhou
- **THEN** Detalhes permanece pendente e a interface apresenta o estado real com orientação de aguardar ou corrigir, sem informar conclusão nem permitir salvar e avançar

#### Scenario: Capa pronta

- **WHEN** a capa da própria galeria está configurada e a API comprova sua prévia pronta
- **THEN** o fotógrafo pode salvar Detalhes e avançar, e a etapa aparece concluída

#### Scenario: Conclusão por outra etapa

- **WHEN** o fotógrafo chega ao botão Concluir por navegação direta ou a capa muda desde a leitura anterior
- **THEN** a interface consulta a prontidão atual do backend e só encerra o fluxo guiado com capa válida pronta; nos demais casos orienta retornar a Detalhes

#### Scenario: Galeria existente sem capa

- **WHEN** o fotógrafo edita ou tenta concluir uma galeria anterior sem capa
- **THEN** o sistema aplica a exigência em Detalhes e na conclusão guiada, preservando dados, pedidos e acesso já autorizado das clientes, sem escolher imagem automaticamente

#### Scenario: Capa removida ou incompatível

- **WHEN** a capa deixa de existir ou referencia foto de outra galeria ou conta
- **THEN** o backend não a considera pronta nem permite salvamento visual com base nesse identificador, e o estado de Detalhes retorna a pendente
