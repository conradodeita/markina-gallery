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

### Requirement: Gate de homologação da autenticação

O sistema SHALL ter um procedimento de homologação para a autenticação que exija inventário somente-leitura, isolamento da Markina Gallery, configuração externa de segredos, aplicação explícita de migrations e smoke tests antes de receber tráfego de teste.

#### Scenario: Plano de impacto zero aprovado

- **WHEN** o operador concluir o inventário do servidor de homologação
- **THEN** ele apresenta ao proprietário os recursos existentes, a porta e o subdomínio propostos, o escopo limitado à Markina Gallery e aguarda aprovação explícita antes de alterar o ambiente

#### Scenario: Preparação de banco e segredos

- **WHEN** a homologação for aprovada
- **THEN** o operador cria recursos exclusivos da Markina Gallery, mantém segredos fora do Git, aplica a migration Alembic de forma explícita e não expõe PostgreSQL nem Redis publicamente

#### Scenario: Entrada HTTPS compartilhada e isolada

- **WHEN** o Proxy Manager for necessário para expor a homologação
- **THEN** o operador conecta somente o nginx da Markina à rede de entrada autorizada com alias exclusivo, cria somente um host novo e certificado para o subdomínio de homologação, e não altera recursos existentes de outros projetos

#### Scenario: Verificação e rollback da autenticação

- **WHEN** a versão de homologação estiver disponível
- **THEN** o operador executa healthchecks e smoke tests de autenticação, registra o resultado e consegue retornar somente a Markina Gallery à versão anterior saudável
