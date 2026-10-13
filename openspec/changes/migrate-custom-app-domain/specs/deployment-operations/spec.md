## ADDED Requirements

### Requirement: Migração de domínio isolada da Markina Gallery

O operador SHALL adicionar um hostname HTTPS da Markina Gallery sem remover o hostname anterior durante a validação. SHALL alterar somente o registro DNS do subdomínio solicitado e adicionar um host virtual/certificado próprios no proxy compartilhado existente, sem mudar seus serviços, portas, redes, firewall ou configurações de terceiros. O domínio raiz SHALL permanecer sem destino de aplicação enquanto reservado ao site institucional futuro.

#### Scenario: Novo hostname validado

- **WHEN** DNS resolve ao destino confirmado e o certificado corresponde ao novo subdomínio
- **THEN** requisições HTTPS ao novo hostname chegam à aplicação Markina e os healthchecks passam

#### Scenario: Hostname anterior durante a transição

- **WHEN** o novo hostname está em validação
- **THEN** o hostname anterior e seu certificado continuam disponíveis e as operações da aplicação aceitam ambas as origens configuradas

#### Scenario: Domínio raiz reservado

- **WHEN** a migração do subdomínio é configurada
- **THEN** nenhum redirecionamento ou serviço de aplicação é criado para o domínio raiz

#### Scenario: Reversão limitada

- **WHEN** o novo hostname falha na validação
- **THEN** o operador remove somente o registro, host virtual e certificado criados para a mudança e restaura a configuração da Markina, preservando serviços compartilhados e o hostname anterior

#### Scenario: Encerramento da origem temporária

- **WHEN** a origem nova foi autenticada e validada e o proprietário encerra a transição
- **THEN** a aplicação deixa de aceitar a origem DuckDNS e o operador remove somente o host virtual Markina antigo do proxy; a conta DNS DuckDNS externa não é alterada
