## ADDED Requirements

### Requirement: Ajuste independente na etapa 04

O sistema SHALL permitir ao admin configurar ativação, intensidade de 10 a 75% e exposição de -2 a +2 EV na etapa 04 de cada galeria. Novas galerias SHALL começar desligadas; a migração SHALL preservar configurações e resultados existentes com exposição zero.

#### Scenario: Isolamento de configurações
- **WHEN** o fotógrafo salva uma nova exposição na galeria A
- **THEN** apenas A muda de geração, sem cancelar processamento ou invalidar resultados de B

#### Scenario: Reprocessamento explícito
- **WHEN** o fotógrafo salva os ajustes e solicita processar a galeria
- **THEN** as fotos elegíveis de todas as suas pastas são enfileiradas sem duplicação, com progresso e comparação antes/depois

### Requirement: Exposição não cumulativa e reversão

O sistema SHALL aplicar a exposição após o ajuste automático sobre a prévia limpa e antes da proteção, preservando originais e entrada facial. Desligar a galeria SHALL restaurar a entrega convencional; falhas SHALL manter o fallback.

#### Scenario: Nova exposição durante processamento
- **WHEN** uma foto termina com geração anterior à configuração salva
- **THEN** o worker não publica o resultado obsoleto

#### Scenario: Repetição de ajuste
- **WHEN** a mesma exposição é reprocessada
- **THEN** o ponto de partida continua sendo a prévia limpa, não o JPEG previamente ajustado

#### Scenario: Limpeza exclusiva
- **WHEN** existe qualquer galeria com o módulo ligado ou o worker não foi declarado parado
- **THEN** a limpeza recusa a execução destrutiva
