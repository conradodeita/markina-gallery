# tenant-foundation Specification

## Purpose

Estabelecer propriedade explícita do acervo do fotógrafo atual e preservar seu legado, preparando a evolução arquitetural sem liberar operação com fotógrafos independentes antes dos testes de isolamento.

## Requirements

### Requirement: Propriedade explícita do acervo

O sistema SHALL associar cada galeria de origem, galeria privada e foto a uma conta de fotógrafo identificada por UUID, mantendo o mesmo proprietário em toda relação entre essas entidades. O sistema MUST rejeitar criação ou associação com proprietário ausente ou incompatível, inclusive em processamento assíncrono.

#### Scenario: Criação de galeria e foto
- **WHEN** o administrador autorizado cria uma galeria e envia fotos
- **THEN** a propriedade da galeria é obtida do contexto autorizado no servidor e a propriedade das fotos e galerias privadas é herdada da origem persistida

#### Scenario: Associação incompatível
- **WHEN** uma foto ou galeria privada é associada a uma origem com proprietário diferente em teste sintético de integridade
- **THEN** a persistência é rejeitada sem alterar os registros ou arquivos existentes

#### Scenario: Processamento posterior ao envio
- **WHEN** um worker processa uma foto de um lote aceito
- **THEN** ele obtém a propriedade da foto e da origem persistidas, valida sua consistência e não aceita um proprietário fornecido pelo payload como autoridade

### Requirement: Migração verificável do fotógrafo atual

O sistema SHALL migrar o acervo legado e os administradores existentes para a conta única do fotógrafo atual, preservando identificadores, relações, autorizações de clientes, valores comerciais e referências aos arquivos. O processo MUST interromper sem alteração parcial caso detecte vínculos órfãos ou incompatíveis.

#### Scenario: Legado consistente
- **WHEN** a migração é executada sobre uma base consistente do fotógrafo atual
- **THEN** todas as entidades afetadas possuem proprietário válido e os identificadores e vínculos anteriores permanecem preservados

#### Scenario: Legado inconsistente
- **WHEN** a conferência encontra foto ou galeria privada sem origem válida
- **THEN** a migração não conclui e registra a inconsistência sem inventar proprietário nem excluir dados

#### Scenario: Instalação vazia
- **WHEN** as migrations e o seed administrativo autorizado são executados em banco vazio
- **THEN** existe uma única conta de fotógrafo e o administrador inicial possui vínculo explícito com ela, sem criação ou alteração automática de credenciais

### Requirement: Operação restrita a um fotógrafo nesta etapa

O sistema SHALL operar nesta entrega somente com uma conta de fotógrafo ativa e única na instalação, sem disponibilizar cadastro ou ativação de outra conta. O sistema MUST interromper operações protegidas e processamento de domínio se houver ausência, suspensão ou multiplicidade de contas, sem escolher arbitrariamente um contexto.

#### Scenario: Conta única válida
- **WHEN** a instalação contém a conta única ativa e os vínculos válidos
- **THEN** o fotógrafo e os clientes continuam os fluxos existentes de galerias, OTP, prévias protegidas e compra conforme suas autorizações

#### Scenario: Contexto de instalação inválido
- **WHEN** a conta é suspensa ou uma segunda conta é inserida por manipulação sintética do banco
- **THEN** a aplicação e os workers recusam operações de domínio sem expor acervos nem publicar resultados ou mensagens

### Requirement: Continuidade da conta após limpeza autorizada de homologação

O procedimento de limpeza dos dados de negócio em homologação SHALL preservar a conta do fotógrafo, seus vínculos administrativos e os meios de acesso existentes. A limpeza MUST manter a conexão/configuração da Evolution e os recursos de infraestrutura correspondentes, respeitando a autorização humana e o inventário próprios da operação.

#### Scenario: Descarte autorizado do acervo de teste
- **WHEN** o operador executa a limpeza autorizada dos dados de negócio em homologação
- **THEN** galerias, fotos e clientes de teste podem ser removidos, enquanto a conta/vínculos do fotógrafo, suas sessões administrativas e as configurações do canal permanecem utilizáveis
