# Spec Delta

## ADDED Requirements

### Requirement: Configuração independente de processamento para pastas públicas

Cada pasta pública de conteúdo SHALL ter configuração própria para ajuste automático de prévias e permissão local de reconhecimento facial. Ao criar uma pasta pública, o sistema SHALL iniciar o ajuste automático ligado, copiando a intensidade e a exposição atuais da galeria, ou usando 50%/0,0 EV quando não houver configuração explícita; SHALL iniciar a permissão facial local como ativa. Os gates globais, de galeria, de autorização e privacidade facial SHALL continuar aplicáveis.

#### Scenario: Nova pasta com parâmetros configurados na galeria

- **WHEN** uma pasta pública é criada enquanto a galeria tem parâmetros de ajuste definidos, com o ajuste ligado ou desligado
- **THEN** a pasta inicia com ajuste ativo e com a intensidade e exposição vigentes na galeria

#### Scenario: Nova pasta sem parâmetros explícitos na galeria

- **WHEN** uma pasta pública é criada enquanto não há configuração explícita de parâmetros na galeria
- **THEN** a pasta inicia com ajuste ligado em 50% e 0,0 EV

#### Scenario: Alteração posterior na galeria

- **WHEN** o fotógrafo altera os controles de ajuste da galeria após criar uma pasta
- **THEN** as configurações e filas das pastas já existentes permanecem inalteradas; somente pastas criadas depois recebem os novos parâmetros, sempre com ajuste ligado

#### Scenario: Isolamento entre pastas

- **WHEN** o fotógrafo altera os controles de processamento de uma pasta pública
- **THEN** nenhuma outra pasta ou a configuração da galeria é alterada

#### Scenario: Pastas públicas já existentes

- **WHEN** a migration aditiva é aplicada
- **THEN** cada pasta pública de conteúdo sem configuração própria recebe um snapshot da intensidade e exposição vigentes, inicia com ajuste ligado e deixa de herdar futuras alterações

#### Scenario: Pasta privada pronta por padrão

- **WHEN** uma pasta privada é criada ou configurada
- **THEN** a prévia continua ativa em 75%/0,0 EV por padrão, o reconhecimento facial continua permitido por pasta, e nenhum valor é copiado da configuração da galeria pública

