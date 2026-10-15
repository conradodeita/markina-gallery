# Spec Delta

## ADDED Requirements

### Requirement: Job de produção é disparado automaticamente após CI
Um workflow SHALL iniciar automaticamente a publicação do SHA aprovado para `main` após CI e validações obrigatórias concluírem com sucesso. O job SHALL aguardar aprovação do ambiente protegido e SHALL repetir inventário de produção, conferir o SHA e limitar mutações aos serviços Pick-your-Pic explicitamente incluídos no plano aprovado.

#### Scenario: CI verde após merge
- **WHEN** um PR aprovado é integrado à `main` e todos os jobs obrigatórios terminam com sucesso
- **THEN** o GitHub inicia automaticamente o job de publicação e o mantém aguardando aprovação do ambiente `production` antes de qualquer mutação remota

#### Scenario: CI falha ou aprovação não é concedida
- **WHEN** uma validação obrigatória falha ou o ambiente protegido não aprova a execução
- **THEN** nenhum comando de mutação é executado em produção

#### Scenario: Inventário ou SHA diverge
- **WHEN** o inventário imediatamente anterior não corresponde ao plano aprovado, o SHA não é o candidato aprovado ou serviços/portas de terceiros seriam afetados
- **THEN** o job falha fechado antes de alterar o ambiente e registra o motivo sem expor segredos

#### Scenario: Publicação de alteração facial atravessa serviços
- **WHEN** a versão altera API, web ou workers faciais
- **THEN** o workflow publica o conjunto de serviços necessário conforme inventário e plano aprovados, sem usar o procedimento limitado ao serviço `web` como substituto de uma publicação integral
