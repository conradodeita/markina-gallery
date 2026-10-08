# Spec Delta

## ADDED Requirements

### Requirement: Controles da sessão separados da navegação do fotógrafo

O sistema SHALL apresentar a identidade autenticada do fotógrafo, o controle de notificações e a ação de saída na barra superior junto às opções de aparência, mantendo esses controles fora da faixa de navegação administrativa.

#### Scenario: Cabeçalho administrativo autenticado
- **WHEN** o fotógrafo acessa uma tela administrativa autenticada
- **THEN** os controles “Logado como”, “Ativar notificações” e “Sair” aparecem na barra superior junto a Aparência, e as opções de navegação permanecem visíveis em sua própria faixa

#### Scenario: Largura reduzida
- **WHEN** a tela administrativa é exibida em uma janela estreita
- **THEN** os controles podem quebrar linha na barra superior sem sobrepor ou ocultar opções do menu
