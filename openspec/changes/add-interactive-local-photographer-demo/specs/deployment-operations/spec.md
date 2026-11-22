## ADDED Requirements

### Requirement: Demonstração interativa e isolada do cadastro SaaS

O projeto SHALL permitir uma demonstração opt-in do cadastro de fotógrafo em loopback com dados sintéticos e banco descartável exclusivo. O executor MUST recusar ambiente protegido e URL de banco fora da identidade local permitida. A inicialização MUST recusar banco preexistente; a retomada SHALL conferir somente por leitura a revisão esperada, sem migration. E-mail e anti-bot sintéticos SHALL existir somente no processo da demonstração, sem habilitar o provider público da aplicação normal.

#### Scenario: Cadastro local
- **WHEN** operador inicia a demonstração em ambiente local vazio e o fotógrafo usa endereço `example.test`
- **THEN** a UI permite receber o código sintético na caixa local, verificar e-mail, configurar senha/TOTP e entrar no tenant criado

#### Scenario: Destino indevido
- **WHEN** o executor recebe banco, host, ambiente ou origem diferente dos permitidos
- **THEN** recusa inicializar antes de qualquer migration ou serviço

#### Scenario: Encerramento
- **WHEN** o operador encerra a demonstração
- **THEN** somente processos e contêiner exclusivos da demonstração são parados, preservando serviços e dados existentes

#### Scenario: Retomada após encerramento da API
- **WHEN** o banco descartável ainda está ativo e registra a revisão esperada
- **THEN** a API sintética pode voltar em loopback sem migration ou exclusão; contas de sessão anterior podem não autenticar porque a chave efêmera anterior não foi persistida

#### Scenario: Runtime local evoluiu depois da demonstração inicial
- **WHEN** os runners de cadastro e encerramento preparam um banco novo para o código atual
- **THEN** a revisão nomeada deve fornecer as colunas usadas pelos modelos e fixtures atuais, mantendo os guards de destino e banco vazio; a retomada recusa schema antigo sem migrá-lo e o smoke de cadastro envia a declaração explícita de maioridade
