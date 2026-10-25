## MODIFIED Requirements

### Requirement: Segredos fora do Git
Segredos e chaves mestras SHALL existir somente em configuração segura do servidor não versionada. Credenciais InfinitePay cadastradas pela UI SHALL permanecer cifradas em armazenamento dedicado com chave mestra externa ao banco. O repositório SHALL ignorar `.env*`, exceto `.env.example`.

#### Scenario: Verificação de ignore
- **WHEN** `.env`, `.env.local`, `.env.homolog` ou `.env.prod` existem no projeto
- **THEN** o Git os ignora e `.env.example` permanece versionável

#### Scenario: Varredura de segredos
- **WHEN** a varredura de segredos é executada no repositório
- **THEN** nenhum segredo ou chave é encontrado

#### Scenario: Recuperação da credencial cifrada
- **WHEN** um backup de banco é restaurado em ambiente autorizado
- **THEN** somente a API com o keyring correspondente e ambiente original pode decifrar credenciais
- **AND** o material criptográfico é recuperado de backup seguro separado do banco

## ADDED Requirements

### Requirement: Classificação do cofre em ferramentas de homologação
Ferramentas de limpeza SHALL classificar `infinitepay_credential` como configuração do tenant. A limpeza de tenant único SHALL preservar seus envelopes. O reset proprietário já autorizado SHALL preservar todas as versões do proprietário e remover somente as versões dos tenants elegíveis à remoção pela política existente, sem imprimir ou decifrar segredos.

#### Scenario: Reset com cinco contas sintéticas
- **WHEN** o reset proprietário é ensaiado em PostgreSQL descartável com credenciais de cinco tenants
- **THEN** todas as versões, ciphertext, nonce e referências de configuração do proprietário permanecem idênticos
- **AND** credenciais dos outros tenants seguem a exclusão existente sem violar FKs
- **AND** inventário e relatório expõem somente contagens

### Requirement: Validação nativa das imagens nas arquiteturas suportadas
O CI desta change SHALL validar as imagens AMD64 e ARM64 em runners nativos das respectivas arquiteturas, com ambos os resultados obrigatórios no gate existente. O ensaio SHALL conservar builds, conferência das versões do lockfile e proibição de publicação/início de serviços operacionais.

#### Scenario: Falha em uma arquitetura
- **WHEN** qualquer build nativo obrigatório falha ou é cancelado
- **THEN** o resultado agregado de imagens impede aprovação do CI
- **AND** nenhuma imagem ou serviço é publicado
