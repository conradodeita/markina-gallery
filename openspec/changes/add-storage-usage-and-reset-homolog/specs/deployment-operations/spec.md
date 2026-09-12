## ADDED Requirements

### Requirement: Higienização descartável de homologação sem backup novo

O sistema SHALL permitir uma higienização destrutiva sem criação de novo backup somente no ambiente de homologação, mediante inventário imediatamente anterior, confirmação literal exclusiva e autorização humana explícita que dispense recuperação. A operação SHALL permanecer limitada ao PostgreSQL, Redis e raízes de mídia do projeto `markina-gallery`.

#### Scenario: Execução autorizada sem backup

- **WHEN** o proprietário declara descartáveis os dados de teste, dispensa backup e fornece autorização explícita para a execução
- **THEN** a automação registra o inventário agregado anterior e exige o token literal específico do modo sem backup
- **AND** não cria novo dump do banco antes da exclusão

#### Scenario: Ambiente ou confirmação incorretos

- **WHEN** o ambiente não é homologação ou o token literal não corresponde ao modo solicitado
- **THEN** a automação interrompe sem excluir banco, mídia ou fila

### Requirement: Preservação administrativa durante a higienização

O sistema SHALL remover galerias públicas e privadas, pastas, fotos, clientes e suas dependências operacionais de teste, incluindo seleções, pedidos, comunicações, sessões de cliente, desafios OTP de cliente, mídia e fila exclusiva, enquanto MUST preservar contas, sessões e fatores de acesso administrativos e preferências globais do sistema.

#### Scenario: Limpeza concluída

- **WHEN** a higienização autorizada termina
- **THEN** as contagens de galerias, pastas, fotos, clientes e dependências operacionais ficam zeradas
- **AND** o administrador continua autenticável e suas preferências globais permanecem inalteradas

#### Scenario: Recursos compartilhados no servidor

- **WHEN** a higienização atua no host que também executa outros projetos
- **THEN** nenhuma rede, volume, container, banco, proxy, certificado ou arquivo externo ao projeto `markina-gallery` é alterado

### Requirement: Verificação posterior da higienização

O sistema SHALL reiniciar somente os serviços Markina pausados pela operação e SHALL verificar contagens, mídia, saúde da API e coerência do processamento facial antes de declarar sucesso.

#### Scenario: Pós-condições válidas

- **WHEN** banco, mídia e fila foram higienizados
- **THEN** o inventário posterior mostra zero dados operacionais e zero bytes fotográficos
- **AND** API, web e workers configurados retornam estado saudável com a mesma configuração administrativa
