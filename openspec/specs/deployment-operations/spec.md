# deployment-operations Specification

## Purpose
Define a fundação de operação entregue por esta mudança: Docker Compose com serviços isolados e healthchecks, rede interna, ambientes definidos por variáveis separadas, segredos fora do Git, CI, proteção de branches e documentação de desenvolvimento, deploy e rollback.

## Requirements

### Requirement: Docker Compose com serviços isolados e healthchecks
O projeto SHALL entregar um Docker Compose com serviços `nginx`, `web` (Next.js), `api` (FastAPI), `db` (PostgreSQL), `redis` e `worker`, cada um com healthcheck. Serviços de aplicação SHALL poder ser retomados individualmente sem iniciar implicitamente serviços one-shot de migration. Migration SHALL permanecer uma operação explícita, executada separadamente e somente após verificação da revisão de destino.

#### Scenario: Ambiente local
- **WHEN** o operador executa o Compose do ambiente local
- **THEN** todos os serviços sobem e os healthchecks respondem com sucesso

#### Scenario: Retomada sem migration
- **WHEN** o operador retoma contêineres existentes da aplicação após uma parada controlada
- **THEN** somente os serviços da aplicação solicitados são iniciados, o serviço one-shot `migrate` não é iniciado e o schema ativo permanece inalterado

#### Scenario: Migration explicitamente solicitada
- **WHEN** o operador executa uma liberação autorizada que exige migration
- **THEN** o fluxo verifica a revisão corrente, executa Alembic de forma explícita com a imagem correspondente ao SHA alvo e só então inicia binários compatíveis

#### Scenario: Healthcheck da retomada falha
- **WHEN** qualquer serviço retomado não fica saudável ou os endpoints de saúde local/público falham
- **THEN** o procedimento registra a falha, mantém a migration fora do fluxo de retomada e solicita diagnóstico sem alterar banco, mídia ou serviços vizinhos

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

### Requirement: Limpezas controladas e delimitadas dos dados de teste de homologação

O sistema SHALL fornecer uma operação explícita, inventariada e restrita à homologação para remover galerias, pastas, fotos, clientes, seleções, compras, pedidos, entregas, interações e histórico operacional relacionado, além da mídia e das filas exclusivas desses dados. A operação SHALL preservar conta e sessões administrativas, fatores 2FA, login e instância Evolution, segredos, todas as configurações globais e recursos de outros projetos. Nesta execução autorizada, ela SHALL NOT criar novo backup, executar em produção ou apagar backups preexistentes.

#### Scenario: Inventário anterior

- **WHEN** o operador prepara a limpeza
- **THEN** apresenta contagens e dependências por categoria, raízes de mídia, serviços, porta, subdomínio e itens preservados antes de qualquer mutação

#### Scenario: Execução autorizada

- **WHEN** o proprietário aprova a execução específica após revisar o inventário e o plano de impacto zero
- **THEN** somente os dados de teste e arquivos/filas elegíveis da Markina em homologação são removidos, com registro de resultado e confirmação das contagens zeradas

#### Scenario: Limpeza sem novo backup após deploy validado

- **WHEN** o commit em `develop` contém a sinalização literal de limpeza sem backup e o SHA publicado em homologação corresponde ao SHA explicitamente inventariado
- **THEN** o workflow verifica o SHA e a saúde do serviço, executa a manutenção sem repetir o deploy nem criar backup de pré-deploy e aborta se o código operacional tiver mudado desde o SHA inventariado

#### Scenario: Preservação de credenciais e preferências

- **WHEN** a limpeza termina
- **THEN** a conta admin, 2FA, login/instância Evolution e todas as configurações globais permanecem utilizáveis e com contagens/estado preservados

#### Scenario: Estado vazio confirmado sem novos dados

- **WHEN** o inventário posterior confirma a limpeza e o proprietário dispensa a validação adicional com dados sintéticos temporários
- **THEN** homologação permanece com zero galerias, clientes, fotos, seleções e pedidos, sem segunda operação destrutiva, mantendo as configurações preservadas

#### Scenario: Ambiente ou inventário divergente

- **WHEN** o ambiente não é homologação ou a operação alcançaria tabela, mídia ou serviço fora da lista aprovada
- **THEN** a operação aborta antes da exclusão
