## MODIFIED Requirements

### Requirement: Migração de domínio isolada da Markina Gallery
O operador SHALL publicar o subdomínio solicitado com DNS e HTTPS próprios, mantendo o hostname anterior disponível durante a validação. A configuração SHALL limitar-se à Markina Gallery, preservar o domínio raiz sem destino de aplicação e, após revisão do proprietário, retirar somente o hostname antigo da Markina do proxy compartilhado e da lista de origens aceitas.

#### Scenario: Novo hostname validado
- **WHEN** o DNS resolve ao destino confirmado e o certificado HTTPS corresponde ao novo subdomínio
- **THEN** as requisições ao novo hostname chegam à Markina e os healthchecks passam

#### Scenario: Hostname anterior durante a validação
- **WHEN** o novo hostname ainda está em validação
- **THEN** o hostname anterior continua disponível e as operações aceitam somente as origens HTTPS configuradas explicitamente

#### Scenario: Domínio raiz reservado
- **WHEN** o subdomínio da aplicação é configurado
- **THEN** nenhum serviço ou redirecionamento de aplicação é criado para o domínio raiz

#### Scenario: Encerramento da origem temporária
- **WHEN** o proprietário revisa e encerra a transição após validar o novo hostname
- **THEN** a origem antiga deixa de ser aceita e somente o host virtual antigo da Markina é removido do proxy; o DNS e a conta externa do provedor antigo permanecem inalterados

#### Scenario: Reversão limitada à Markina
- **WHEN** a validação do novo hostname falha
- **THEN** o operador reverte apenas as alterações de DNS e proxy criadas para a Markina e restaura sua configuração anterior, preservando serviços compartilhados e o hostname anterior
