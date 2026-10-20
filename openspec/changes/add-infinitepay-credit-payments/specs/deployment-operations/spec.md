## ADDED Requirements

### Requirement: Deploy de pagamento preserva módulos opcionais
O deploy de uma change de pagamento SHALL preservar o estado operacional pré-existente de módulos opcionais fora do escopo. O workflow MUST NOT habilitar processamento facial nem desenvolvimento RAW por padrão. Para facial, o deploy SHALL manter o valor já persistido; para RAW, SHALL detectar e manter o worker ativo, sem iniciar o worker se estiver inativo.

#### Scenario: Módulos opcionais permanecem inativos
- **WHEN** a publicação de pagamento começa com processamento facial desabilitado e worker RAW inativo
- **THEN** a publicação mantém ambos desabilitados e não inicia seus workers

#### Scenario: Módulos opcionais ativos são preservados
- **WHEN** a publicação de pagamento começa com processamento facial habilitado ou worker RAW ativo
- **THEN** a publicação mantém esses módulos no estado operacional detectado e os atualiza junto com o código

### Requirement: Escopo do release da correção InfinitePay

O release da correção de diagnóstico InfinitePay SHALL permanecer no escopo API/web existente, com blobs runtime limitados aos módulos de emissão de pagamento alterados. O manifesto SHALL fixar os hashes exatos desses módulos. A change MUST NOT alterar schema/migrations, Docker/Compose, workers, Nginx ou serviços de terceiros.

#### Scenario: Gate admite somente os módulos de pagamento revisados
- **WHEN** o classificador de release avalia a correção e seus artefatos de teste/OpenSpec
- **THEN** admite os dois módulos backend incluídos no manifesto e não autoriza mudanças de schema ou infraestrutura
