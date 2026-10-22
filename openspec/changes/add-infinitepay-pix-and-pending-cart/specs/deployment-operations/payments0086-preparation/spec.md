# Spec Delta

## ADDED Requirements

### Requirement: Bootstrap manual preserva recuperação do cofre

O preparador operacional SHALL exigir seleção explícita de provisionamento, terminal interativo, confirmação de senha com pelo menos16caracteres, host/diretório/owner/ambiente esperados e ausência de material existente ou operação pendente. MUST NOT reiniciar aplicação ou alterar pagamentos.

#### Scenario: Material existente ou execução não interativa
- **WHEN** existe keyring/backup/link, há operação pendente ou não há terminal interativo
- **THEN** o preparador recusa antes de gerar/escrever material ativo
- **AND** arquivos existentes permanecem preservados para reconciliação

### Requirement: Material mestre tem backup independente e restrito

O preparador SHALL gerar chave mestra aleatória32bytes, cifrar e verificar backup AES-GCM independente com chave derivada por scrypt fixo antes de escrever material ativo0600. MUST NOT sobrescrever keyrings/backups, imprimir segredos ou passar senha por argumento. Chave mestra SHALL ser fornecida somente à API pela configuração segura já prevista.

#### Scenario: Senha errada ou backup adulterado
- **WHEN** o ensaio tenta restaurar com senha incorreta ou nonce/ciphertext adulterados
- **THEN** a verificação criptográfica recusa sem revelar segredo

### Requirement: Preparação não equivale a publicação

Inventário, smoke e restore sintéticos SHALL distinguir o que foi executado localmente de backup/homologação/custódia reais. O workflow0084 MUST permanecer recusando a candidata0086. Publicação SHALL aguardar plano revisto, inventário atual, imagens fixas, backup real restaurável, custódia externa e barreira ensaiada que preserve retorno e webhook.

#### Scenario: Ensaios sintéticos aprovados
- **WHEN** migrações/restauração/criptografia sintéticas passam e o preparador é disponibilizado sem executá-lo
- **THEN** o relatório informa preparação aprovada e gates operacionais pendentes
- **AND** não declara cofre provisionado, schema migrado ou aplicação publicada
