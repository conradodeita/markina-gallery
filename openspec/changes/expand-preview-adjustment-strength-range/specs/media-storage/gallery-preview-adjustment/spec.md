## ADDED Requirements

### Requirement: Configuração do ajuste de prévias

O sistema SHALL permitir ao administrador configurar ativação, intensidade de 10 a 100% e exposição de -2 a +2 EV no controle de ajuste de prévias aplicável à galeria/pasta. Intensidade de 100% SHALL selecionar integralmente a saída corrigida do motor, sem mistura com a prévia limpa. Exposição continuará independente da intensidade. Defaults existentes SHALL permanecer inalterados.

#### Scenario: Intensidade máxima

- **WHEN** o administrador define a intensidade como 100%
- **THEN** o resultado usa 100% da prévia corrigida e 0% da prévia limpa, mantendo resolução, proteção visual, autorização e a compensação EV configurada

#### Scenario: Intensidade abaixo do máximo

- **WHEN** o administrador define intensidade entre 10% e 99%
- **THEN** o sistema mistura a prévia limpa e a corrigida na proporção informada, sem alterar o ajuste de exposição em EV

#### Scenario: Valor fora da faixa

- **WHEN** uma requisição envia intensidade menor que 10% ou maior que 100%
- **THEN** a API rejeita o valor e nenhuma configuração ou geração é alterada
