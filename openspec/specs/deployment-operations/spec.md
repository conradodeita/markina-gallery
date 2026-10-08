# deployment-operations Specification

## Purpose
Define a fundação de operação entregue por esta mudança: Docker Compose com serviços isolados e healthchecks, rede interna, ambientes definidos por variáveis separadas, segredos fora do Git, CI, proteção de branches e documentação de desenvolvimento, deploy e rollback.

## Requirements

### Requirement: Docker Compose com serviços isolados e healthchecks
O projeto SHALL entregar um Docker Compose com serviços `nginx`, `web` (Next.js), `api` (FastAPI), `db` (PostgreSQL), `redis` e `worker`, cada um com healthcheck.

#### Scenario: Ambiente local
- **WHEN** o operador executa o Compose do ambiente local
- **THEN** todos os serviços sobem e os healthchecks respondem com sucesso

### Requirement: PostgreSQL e Redis sem portas públicas
Os serviços `db` e `redis` SHALL permanecer acessíveis apenas pela rede interna do Compose, sem portas publicadas externamente.

#### Scenario: Inspeção de portas publicadas
- **WHEN** a configuração do Compose é inspecionada
- **THEN** apenas `nginx` possui porta publicada externamente, e `db` e `redis` não publicam portas

### Requirement: Nginx como única porta publicada
O serviço `nginx` SHALL ser a única porta publicada externamente, como entrada única de tráfego para `web` e `api`.

#### Scenario: Topologia de entrada
- **WHEN** um usuário acessa o sistema
- **THEN** a requisição passa pelo `nginx` antes de alcançar `web` ou `api`

### Requirement: Ambientes definidos por variáveis separadas
O projeto SHALL definir os ambientes `local`, `homolog` e `prod` por meio de arquivos `.env.<ambiente>` não versionados, documentados pelo `.env.example`.

#### Scenario: Documentação de variáveis
- **WHEN** o operador prepara um ambiente
- **THEN** o `.env.example` documenta todas as variáveis necessárias, sem valores reais

### Requirement: Segredos fora do Git
Segredos e chaves de API SHALL existir apenas em `.env` não versionado, e o repositório SHALL manter `.env*` ignorado com exceção de `.env.example`.

#### Scenario: Verificação de ignore
- **WHEN** `.env`, `.env.local`, `.env.homolog` ou `.env.prod` existem no projeto
- **THEN** o Git os ignora e `.env.example` permanece versionável

#### Scenario: Varredura de segredos
- **WHEN** a varredura de segredos é executada no repositório
- **THEN** nenhum segredo ou chave é encontrado

### Requirement: CI com lint, testes e build
O projeto SHALL entregar workflows de CI que executam lint, testes e build, além de validação OpenSpec, em pull requests.

#### Scenario: Pull request
- **WHEN** um pull request é aberto
- **THEN** lint, testes, build e validação OpenSpec são executados

### Requirement: Repositório com branches protegidas
O repositório SHALL adotar `main` protegida por convenção — alterações somente via pull request com CI verde e revisão —, além de `develop` e branches de funcionalidade, com Conventional Commits documentados. O enforcement técnico de proteção de branch no GitHub permanece pendente de plano compatível (recurso pago em repositórios privados; decisão do proprietário: manter o plano gratuito).

#### Scenario: Alteração direta na main
- **WHEN** alguém tenta alterar a `main` diretamente
- **THEN** o fluxo de trabalho exige pull request com CI verde e revisão antes do merge, conforme a convenção documentada

### Requirement: Documentação de desenvolvimento, deploy e rollback
O projeto SHALL documentar desenvolvimento, deploy de homologação/produção, decisões técnicas e checklist de rollback.

#### Scenario: Consulta de procedimentos
- **WHEN** o operador precisa configurar o ambiente ou reverter uma versão
- **THEN** README, DEPLOY.md, decisões técnicas e checklist de rollback orientam o procedimento

### Requirement: Inventário manual e somente leitura da homologação
O projeto SHALL fornecer em `main` um workflow manual dedicado a inventariar a homologação sem compartilhar o caminho de execução destrutivo de manutenção.

#### Scenario: Invocação controlada
- **WHEN** um operador inicia o workflow manual a partir de `main`
- **THEN** o workflow SHALL exigir o SHA completo esperado da versão implantada, usar o ambiente protegido `homolog`, permissões mínimas e validação estrita da chave SSH do host
- **AND** SHALL interromper antes de coletar dados se o HEAD implantado em `/opt/markina-gallery` não corresponder ao SHA informado

#### Scenario: Escopo isolado da Markina Gallery
- **WHEN** o inventário é executado no servidor
- **THEN** SHALL usar somente `/opt/markina-gallery`, `docker/docker-compose.yml`, o arquivo de ambiente homolog e o projeto Compose `markina-gallery`
- **AND** SHALL validar que somente nginx publica porta e que volumes consultados são volumes nomeados exclusivos do projeto, sem referências externas
- **AND** SHALL informar versão implantada, serviços e estado de saúde, portas publicadas, domínio público configurado, revisão Alembic, contagens agregadas de dados e mídia, estado agregado das filas, health endpoints e capacidade do disco
- **AND** SHALL criar e remover exatamente um container transitório de consulta com `--rm --no-deps`, dentro do projeto Compose `markina-gallery`

#### Scenario: Minimização de dados
- **WHEN** o resultado do inventário é apresentado nos logs do Actions
- **THEN** SHALL omitir PII, segredos, caminhos/nome/conteúdo de arquivos e payloads de jobs
- **AND** SHALL apresentar somente contagens agregadas necessárias à avaliação operacional

#### Scenario: Sem efeitos de deploy ou manutenção
- **WHEN** o inventário é executado
- **THEN** SHALL NOT executar deploy, migration, backup, stop, restart, remoção persistente, limpeza ou prune
- **AND** SHALL NOT alterar recursos de outros projetos
- **AND** SHALL limitar consultas de aplicação a um único container transitório de consulta com `--rm --no-deps`, dentro do projeto Compose `markina-gallery`
- **AND** SHALL manter a operação destrutiva de manutenção fora deste workflow
