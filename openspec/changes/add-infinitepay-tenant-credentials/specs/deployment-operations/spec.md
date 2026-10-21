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
