## ADDED Requirements

### Requirement: Progresso de upload visível por pasta

Na etapa Imagens, o sistema SHALL exibir o progresso de cada lote de upload junto à pasta de destino, sem depender de qual pasta está selecionada. Atualizações de progresso SHALL preservar a tela estável enquanto o upload está ativo.

#### Scenario: Lote ativo em outra pasta

- **WHEN** o fotógrafo navega entre pastas enquanto um lote continua sendo enviado
- **THEN** o indicador do lote permanece visível e associado à pasta correta

#### Scenario: Atualização de processamento em segundo plano

- **WHEN** o sistema consulta o estado de preparação das fotos durante um upload
- **THEN** a consulta não causa piscada na tela nem remove o contador do upload
