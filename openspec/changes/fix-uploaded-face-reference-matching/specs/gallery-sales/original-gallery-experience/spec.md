# Spec Delta

## ADDED Requirements

### Requirement: Conclusão da busca iniciada conduz às fotos encontradas

Quando uma consulta facial iniciada pela cliente na página atual concluir em `ready` com candidatas autorizadas renderizáveis, a interface SHALL fechar a ampliação e conduzir uma única vez ao bloco `Possibilidades encontradas`, com foco acessível. A regra SHALL cobrir toque, referência do dispositivo e captura de câmera.

#### Scenario: Upload termina enquanto a cliente explora a galeria
- **WHEN** uma busca enviada nesta página termina com candidatas enquanto a cliente está rolada ou com uma foto ampliada
- **THEN** a ampliação fecha e o título dos resultados e as possibilidades ficam acessíveis sem precisar localizar o bloco abaixo da capa

#### Scenario: Consulta por toque conclui
- **WHEN** a consulta iniciada ao tocar no rosto fica pronta com candidatas
- **THEN** o mesmo mecanismo único conduz ao bloco e não repete saltos a cada atualização
- **AND** esse direcionamento substitui o retorno exclusivo ao topo descrito em `simplify-mobile-gallery-face-search`

#### Scenario: Resultado restaurado ou mesma consulta recebida novamente
- **WHEN** a tela restaura uma consulta antiga ou repete o estado pronto já apresentado
- **THEN** a posição de leitura é preservada

#### Scenario: Barra chega a 100 antes da organização terminar
- **WHEN** os contadores chegam ao total mas o estado ainda é `searching` ou `ranking`
- **THEN** a interface continua esperando o resultado terminal sem navegar prematuramente

#### Scenario: Nenhuma candidata ou falha
- **WHEN** a consulta termina sem candidatas, falha, expira ou é cancelada
- **THEN** a mensagem sanitizada aparece no painel e o acervo manual permanece disponível, sem navegar para um bloco inexistente
