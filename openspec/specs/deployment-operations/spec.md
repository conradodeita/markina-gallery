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

### Requirement: Entrega compreensível e verificável por deploy

O operador SHALL apresentar antes de cada deploy o escopo concreto, inventário atualizado, portas/subdomínio, impacto previsto, validações e reversão, aguardando autorização humana explícita. Após a execução, SHALL registrar em português simples o que foi efetivamente entregue, o que o proprietário pode testar, as verificações realizadas e o que ficou pendente, identificando ambiente, data, versão da aplicação e revisão do banco. Um deploy MUST ser declarado validado somente com evidência dos critérios de aceite daquela etapa.

#### Scenario: Liberação bem-sucedida da fundação
- **WHEN** o deploy autorizado da fundação passa pelos testes de aceite
- **THEN** o proprietário recebe um registro que explica a propriedade do acervo, orienta um teste do fluxo atual e informa que múltiplos fotógrafos ainda não estão habilitados

#### Scenario: Verificação pendente ou falha
- **WHEN** a versão é publicada mas uma verificação necessária falha ou depende de participação humana
- **THEN** o registro informa a publicação e sua limitação sem declarar a etapa validada, documentando a correção ou reversão aplicável

### Requirement: Paridade comprovada antes de migration remota

O operador SHALL comparar a versão/schema do destino com o histórico de migrations e a versão selecionada para liberação antes de executar migration remota. Divergência não reconciliada MUST impedir o deploy, preservando a base existente e o trabalho local.

#### Scenario: Histórico remoto posterior ao checkout
- **WHEN** o destino registra uma migration ausente na versão selecionada
- **THEN** a liberação é suspensa até identificar e reconciliar a origem dessa migration, sem downgrade, carimbo de revisão ou substituição do histórico para contornar a divergência

#### Scenario: Histórico compatível
- **WHEN** a revisão real do destino pertence à cadeia validada e a aplicação de destino está identificada
- **THEN** o operador registra a evidência e pode apresentar o plano de migration e deploy para autorização

### Requirement: Interrupção restrita dos escritores antes da migration

O deploy autorizado SHALL construir as imagens antes da janela, interromper somente API e workers ativos do projeto `markina-gallery` e verificar a interrupção antes de executar Alembic. Jobs duráveis SHALL permanecer no banco para retomada com a versão compatível. Serviços, volumes e configuração da Evolution e dos projetos vizinhos MUST permanecer preservados. Falha de interrupção MUST impedir a migration; mudança de schema MUST impedir retorno automático ao binário anterior incompatível.

A origem pública já configurada corretamente SHALL ser conferida sem reescrever o arquivo de ambiente. Configuração divergente ou ausente SHALL exigir autorização humana específica antes de sua alteração.

#### Scenario: Escritores interrompidos
- **WHEN** as imagens estão prontas e os escritores exclusivos são interrompidos e conferidos
- **THEN** a migration pode iniciar, seguida dos binários compatíveis e dos testes de aceite

#### Scenario: Escritor ainda ativo
- **WHEN** algum escritor continua em execução ou sua parada falha
- **THEN** Alembic não é executado e a falha é registrada para recuperação segura

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

### Requirement: Release pontual de pagamentos preserva produção existente
O release da melhoria de situações financeiras SHALL preservar os comportamentos da versão de produção `71be3b29659143293351968e15fb4886c2d72bf0`, integrar o delta aprovado de pagamentos por PR validado e atualizar somente API/web, admitindo recarga do nginx da Markina para resolução do upstream. O release SHALL NOT executar migrations, atualizar workers, modificar configurações ou dados nem alterar recursos de terceiros.

#### Scenario: Candidato anterior ao código implantado
- **WHEN** a main não contém correções presentes na versão instalada
- **THEN** o executor reconcilia a candidata, valida o resultado e não publica uma versão que remova essas correções

#### Scenario: Publicação aprovada
- **WHEN** inventário, SHA, imagens de recuperação, domínio, portas, escopo e possível interrupção são conferidos e aprovados pelo proprietário
- **THEN** o executor preserva as imagens existentes, constrói API/web, recria somente esses serviços sem dependências e verifica saúde e acesso HTTPS

#### Scenario: Configuração ou estado divergente
- **WHEN** revisão de banco, manifesto Compose, hashes de configuração, imagens ou checkout diferem do inventário aprovado
- **THEN** a publicação para antes de trocar containers e exige reavaliação do inventário

#### Scenario: Recuperação necessária
- **WHEN** o release falha e a recuperação das imagens anteriores foi explicitamente aprovada
- **THEN** o executor restaura somente API/web e checkout anterior, recarrega o nginx da Markina e verifica saúde, sem tocar banco ou recursos de terceiros
