## ADDED Requirements

### Requirement: Seletor facial tem apresentação compacta e responsiva

O painel do proprietário SHALL agrupar o motor selecionado e um único botão “Usar SFace” ou “Usar Gemma” em uma faixa de ação. O alcance global e o uso de SFace por galerias antigas ou sem cobertura Gemma completa SHALL permanecer visíveis. Indicadores agregados e aviso de limiar não calibrado SHALL estar em detalhes expansíveis acessíveis por teclado, recolhidos inicialmente. A apresentação SHALL seguir os tokens da página e evitar overflow horizontal em telas pequenas.

#### Scenario: Proprietário consulta a configuração

- **WHEN** o proprietário abre Configurações com resposta autorizada do endpoint existente
- **THEN** o painel SHALL mostrar o motor selecionado e o botão de troca, sem expor uma lista técnica extensa inicialmente
- **AND** abrir os detalhes SHALL mostrar prontidão do processamento, faces indexadas, jobs aguardando e a limitação de calibração sem alterar o motor

#### Scenario: Proprietário usa celular

- **WHEN** a página está em viewport estreita
- **THEN** a faixa de ação SHALL empilhar o motor e o botão, mantendo indicadores legíveis e controles com altura mínima de 44 px

#### Scenario: Worker Gemma está indisponível

- **WHEN** SFace está selecionado e o worker Gemma não está pronto
- **THEN** o botão de ativação Gemma SHALL permanecer desabilitado com orientação visível
- **AND** o retorno a SFace quando Gemma está selecionado SHALL permanecer disponível
