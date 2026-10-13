# Spec Delta

## ADDED Requirements

### Requirement: Configuração própria pronta para processamento por pasta

Cada pasta de conteúdo, pública ou privada, SHALL ter configuração própria para ajuste automático de prévias e reconhecimento facial. Ao criar uma pasta, o sistema SHALL iniciar o ajuste automático ligado e SHALL iniciar a permissão facial como ativa, sem copiar configurações da galeria ou de outra pasta. Pastas públicas SHALL iniciar em 50%/0,0 EV e pastas privadas SHALL iniciar em 75%/0,0 EV. Os gates globais, de galeria, de autorização e privacidade facial SHALL continuar aplicáveis às pastas públicas.

#### Scenario: Nova pasta pública sem herança da galeria

- **WHEN** uma pasta pública é criada enquanto a galeria tem parâmetros diferentes dos defaults da pasta
- **THEN** a pasta inicia com ajuste ativo em 50% e 0,0 EV e reconhecimento facial local permitido

#### Scenario: Nova pasta privada sem herança da galeria

- **WHEN** uma pasta privada é criada enquanto a galeria pública tem parâmetros de ajuste diferentes
- **THEN** a pasta inicia com ajuste ativo em 75% e 0,0 EV e reconhecimento facial permitido

#### Scenario: Alteração posterior na galeria

- **WHEN** o fotógrafo altera os controles de ajuste da galeria após criar uma pasta
- **THEN** as configurações e filas das pastas existentes permanecem inalteradas e pastas futuras continuam usando seus próprios defaults, sempre com ajuste ligado

#### Scenario: Isolamento entre pastas

- **WHEN** o fotógrafo altera os controles de processamento de uma pasta pública
- **THEN** nenhuma outra pasta ou a configuração da galeria é alterada

#### Scenario: Pastas públicas já existentes

- **WHEN** a migration aditiva é aplicada
- **THEN** cada pasta pública de conteúdo sem configuração própria recebe um snapshot da intensidade e exposição vigentes, inicia com ajuste ligado e deixa de herdar futuras alterações

#### Scenario: Pasta privada pronta por padrão

- **WHEN** uma pasta privada é criada ou configurada
- **THEN** a prévia continua ativa em 75%/0,0 EV por padrão, o reconhecimento facial continua permitido por pasta, e nenhum valor é copiado da configuração da galeria pública
