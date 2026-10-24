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

### Requirement: Runtime de Vendas e pagamentos tem allowlist API/web exata
O verificador de release API/web SHALL reconhecer somente os arquivos de runtime de pagamentos e exportação enumerados no manifesto, com hashes de blob correspondentes ao candidato.

#### Scenario: Candidato revisado de pagamentos
- **WHEN** o candidato altera os runtimes enumerados e o manifesto contém seus blobs exatos
- **THEN** o classificador aceita o escopo API/web, mantendo o restante da allowlist fechado

#### Scenario: Runtime fora da lista
- **WHEN** o candidato altera um caminho de runtime não enumerado
- **THEN** o verificador recusa o release por divergência de escopo ou blob

### Requirement: Remoção da página de Estatísticas é uma exceção exata do escopo API/web
O verificador SHALL tratar como aposentados somente a página e o teste antigos de Estatísticas, sem listá-los como runtimes ativos.

#### Scenario: Remoção autorizada da rota antiga
- **WHEN** o candidato remove `frontend/app/admin/statistics/page.tsx` e `frontend/app/admin/statistics/page.test.tsx`
- **THEN** o classificador aceita somente essas duas remoções exatas

#### Scenario: Outro caminho de Estatísticas
- **WHEN** o candidato altera qualquer outro caminho sob `frontend/app/admin/statistics/`
- **THEN** o verificador recusa o release por caminho fora do escopo

### Requirement: Sincronizar hashes não aprova uma publicação
Atualizar hashes de runtime MUST NOT alterar baseline de produção, revisão do banco ou estados dos gates operacionais. Um release ainda requer inventário somente-leitura e aprovação protegida do fingerprint e SHA exatos.

#### Scenario: Manifestos sincronizados sem inventário
- **WHEN** os hashes do candidato são sincronizados, sem inventário aprovado
- **THEN** o fluxo não publica nem declara release autorizado

### Requirement: O escopo API/web admite somente os arquivos exatos de coordenação de release já revisados
O verificador de release API/web SHALL permitir, além dos runtimes e artefatos previamente enumerados, somente os arquivos `scripts/deploy-prod-lock.sh`, `scripts/deploy-prod-web.sh`, `scripts/test_deploy_prod_web.sh` e `scripts/test_deploy_prod_web_policy.py` como delta operacional desta integração. A allowlist SHALL NOT aceitar outros caminhos operacionais por diretório ou padrão aproximado.

#### Scenario: Delta inclui a coordenação de release aprovada
- **WHEN** o diff desde o baseline contém um ou mais dos quatro caminhos exatos de coordenação e nenhum caminho fora da allowlist
- **THEN** o verificador mantém elegível somente o escopo API/web com os hashes de runtime já aprovados

#### Scenario: Delta inclui operação não listada
- **WHEN** o diff inclui outro script de deploy ou um arquivo semelhante não enumerado
- **THEN** o verificador recusa o candidato antes do inventário remoto

#### Scenario: Allowlist operacional é reconciliada
- **WHEN** os quatro caminhos exatos são permitidos
- **THEN** o baseline, os hashes de runtime, a revisão do banco e os gates de inventário e aprovação permanecem inalterados

### Requirement: Classificação CI de alterações protegidas
A CI SHALL reportar `protected` como classificação válida sem iniciar publicação automática; somente o workflow manual dedicado pode publicar a aposentadoria. Uma classificação `mixed` MUST continuar falhando fechada.

#### Scenario: Aposentadoria integrada em main
- **WHEN** o push à `main` contém somente a change protegida de aposentadoria
- **THEN** a CI conclui sua classificação com sucesso e não executa os gates de publicação API/web ou facial

#### Scenario: Delta mistura runtimes protegidos
- **WHEN** o classificador detecta um delta `mixed`
- **THEN** o job geral de escopo falha e nenhum release automático é autorizado

### Requirement: Release protegido da aposentadoria InfinitePay
O sistema SHALL oferecer um procedimento de produção exclusivo para aplicar a migration `20261022_0087` e publicar a aposentadoria InfinitePay, condicionado a SHA revisado em `main`, CI aprovado, inventário remoto e aprovação explícita do inventário e do plano de impacto.

#### Scenario: Inventário divergente ou incompleto
- **WHEN** o SHA ativo, schema, serviços, portas, domínio, Compose ou fingerprint diferem dos valores esperados ou do inventário apresentado
- **THEN** o procedimento interrompe antes de alterar banco, containers, segredos ou arquivos do host

### Requirement: Aprovação explícita vinculada ao inventário de aposentadoria
O workflow SHALL separar o preflight somente leitura do release mutável em operações manuais distintas. O release MUST exigir o fingerprint integral apresentado e aprovado pelo operador, executar nova coleta read-only e falhar fechado se o valor informado não corresponder exatamente ao fingerprint recém-coletado. A existência do ambiente GitHub `production` não substitui esse gate.

#### Scenario: Preflight somente leitura
- **WHEN** o operador despacha `infinitepay-retirement-preflight`
- **THEN** o workflow executa apenas escopo e inventário remoto read-only e não inicia qualquer job de release, mesmo quando o inventário produz fingerprint válido

#### Scenario: Release com inventário aprovado e inalterado
- **WHEN** o operador despacha `infinitepay-retirement-release` com o fingerprint apresentado e aprovado, CI passa e o novo inventário remoto produz o mesmo fingerprint
- **THEN** o gate de aprovação passa e o job mutável pode iniciar usando a credencial de produção

#### Scenario: Fingerprint ausente, inválido ou divergente
- **WHEN** o fingerprint informado está ausente, tem formato inválido ou diverge do inventário recém-coletado
- **THEN** o gate falha e o job mutável não inicia

### Requirement: Validação read-only do recibo de restauração protegido
O release SHALL validar o recibo de restauração e o checksum do backup com privilégio não interativo, preservando o owner root e o modo `0600`; a falha da validação MUST interromper a execução antes de qualquer alteração.

#### Scenario: Recibo legível somente por root
- **WHEN** a conta SSH de release não pode ler o recibo `0600`
- **THEN** o verificador executa somente a leitura e o cálculo de checksum via `sudo -n`, não altera permissões ou owner e falha fechado se `sudo` ou qualquer validação não passar

#### Scenario: Migration aplicada ao schema esperado
- **WHEN** o inventário aprovado confirma a revisão anterior exata e o backup anterior é verificável
- **THEN** o procedimento aplica somente a migration `20261022_0087`, confirma a nova revisão e preserva pedidos, pagamentos, tentativas, recibos, correções e relações financeiras

#### Scenario: Recuperação após falha de migration
- **WHEN** a migration iniciou e o release falha antes da validação final
- **THEN** o procedimento interrompe novas alterações e exige restaurar o backup de banco aprovado antes de qualquer rollback de aplicação

### Requirement: Remoção delimitada do binding InfinitePay no host
O sistema SHALL remover do host somente o arquivo de binding InfinitePay comprovadamente exclusivo, após a versão sem mount estar ativa e saudável, sem exibir ou copiar seu conteúdo.

#### Scenario: Binding exclusivo identificado
- **WHEN** o inventário confirma caminho, tipo e uso exclusivo do arquivo pelo serviço da Markina e a versão publicada já não o referencia
- **THEN** o procedimento remove somente esse arquivo e registra o resultado sem revelar conteúdo ou valor de segredo

#### Scenario: Binding compartilhado, inesperado ou ambíguo
- **WHEN** o arquivo é usado por outro projeto, é link simbólico, ou seu caminho/escopo não corresponde ao inventário aprovado
- **THEN** o procedimento não o remove e interrompe essa etapa para revisão humana

### Requirement: Cobertura do inventário de referências do binding
O inventário SHALL verificar referências em arquivos Compose das raízes compartilhadas e mounts bind de todos os containers existentes. Falha de leitura, erro do daemon ou inventário parcial MUST bloquear a aprovação de exclusividade e a remoção.

#### Scenario: Varredura incompleta
- **WHEN** a leitura de qualquer raiz ou inspeção do daemon falha ou fica incompleta
- **THEN** a aprovação de exclusividade e a remoção do binding são bloqueadas

### Requirement: Gate pré-release para referências do binding
O preflight SHALL permitir somente a referência do Compose ativo antes do release. Referências adicionais ou no Compose alvo MUST bloquear a aprovação.

#### Scenario: Apenas a referência do Compose ativo
- **WHEN** o preflight encontra somente /opt/markina-gallery/docker/docker-compose.yml e markina-gallery/api como consumidor, sem referências no Compose alvo ou em outra configuração
- **THEN** o inventário pode emitir fingerprint para apresentação, mas a remoção permanece bloqueada até a versão sem mount ficar ativa e saudável

### Requirement: Manifesto do runtime API/web após a aposentadoria
O gate API/web SHALL fixar somente os arquivos de runtime presentes no alvo integrado e permitir caminhos InfinitePay removidos somente quando o diff Git comprova exclusão. Modificação ou reintrodução de caminho aposentado MUST bloquear o gate.

#### Scenario: Caminhos aposentados excluídos
- **WHEN** o diff remove somente os caminhos InfinitePay explicitamente aposentados e os demais blobs coincidem com o manifesto
- **THEN** a validação do manifesto passa sem autorizar o workflow comum para a migration protegida

#### Scenario: Caminho aposentado modificado ou reintroduzido
- **WHEN** um caminho InfinitePay aposentado é modificado ou adicionado novamente
- **THEN** o gate recusa a publicação e não o trata como exclusão aprovada

### Requirement: Continuação do gate após integração da aposentadoria
Após a aposentadoria estar integrada, a CI MAY aceitar um commit de manutenção somente se a base já contiver a migration `20261022_0087`, o Compose não referenciar o binding e o diff estiver limitado à allowlist exata de arquivos operacionais, testes e documentação. Alterações de runtime, migration ou Compose MUST continuar recusadas por esse caminho.

#### Scenario: Ajuste operacional sobre aposentadoria integrada
- **WHEN** um commit subsequente altera somente os arquivos de gate aprovados e a base já contém a migration sem referência ao binding no Compose
- **THEN** a CI valida o ajuste operacional sem reabrir ou republicar o escopo de runtime

#### Scenario: Base ainda não aposentada ou diff amplo
- **WHEN** a base não contém a migration, ainda referencia o binding ou o diff altera runtime
- **THEN** a validação do follow-up falha fechada

### Requirement: Verificação pós-release da aposentadoria InfinitePay
O sistema SHALL verificar saúde local e HTTPS, continuidade do PIX próprio e disponibilidade somente leitura do histórico InfinitePay antes de declarar o release concluído.

#### Scenario: Release saudável e dados históricos preservados
- **WHEN** os healthchecks e smoke tests passam após a nova revisão de schema
- **THEN** o procedimento confirma os registros financeiros preservados por evidência agregada e verifica as duas compras históricas sem mutar seus estados

#### Scenario: Validação pós-release falha
- **WHEN** healthchecks, smoke tests, PIX ou consulta histórica falham
- **THEN** o release permanece inconclusivo, preserva evidências e requer diagnóstico antes de limpar qualquer outro artefato

### Requirement: Parada graciosa do worker durante a migration
O sistema SHALL aguardar o ciclo de trabalho em andamento antes de parar o worker geral da Markina para a migration, e SHALL interromper o release antes de alterar o schema se o container não sair com código zero dentro do timeout explícito.

#### Scenario: Worker conclui o ciclo atual
- **WHEN** o worker recebe SIGTERM durante uma tarefa durável
- **THEN** termina o ciclo em andamento, não inicia outro e sai com código zero antes da migration

#### Scenario: Worker excede o timeout de parada
- **WHEN** o worker não sai com código zero após o timeout configurado
- **THEN** a migration não é iniciada e o runtime anterior é restaurado

#### Scenario: Transição autorizada do worker legado sem handler SIGTERM
- **WHEN** o proprietário autoriza explicitamente indisponibilidade e interrupção do worker legado, sua imagem/source são os inventariados, a API está pausada, não há tarefa ativa/elegível nas filas e o processo principal está ocioso
- **THEN** o executor MAY usar SIGINT por opt-in específico e aceitar exclusivamente saída `130` para esse legado antes da migration, preservando filas e histórico; timeout, SIGKILL, trabalho ativo ou identidade divergente MUST abortar e recuperar o runtime anterior

### Requirement: Continuidade verificável do executor de aposentadoria
O executor SHALL preservar as imagens e o SHA anteriores antes da parada e SHALL encaminhar integralmente a entrada explícita de validação do backup e dos coletores financeiros. Falhas anteriores à migration MUST recuperar o checkout e os containers anteriores sem aplicar migration ou remover o binding.

#### Scenario: Release percorre o fluxo aprovado
- **WHEN** inventário, recibo, build, backup e evidências passam
- **THEN** o executor preserva as imagens por digest, valida o archive recebido por stdin, coleta evidências antes/depois e só limpa o binding após saúde e igualdade financeira

#### Scenario: Falha após pausa e antes da migration
- **WHEN** a validação do backup ou a parada graciosa falha
- **THEN** o executor volta ao SHA observado no inventário, reinicia os mesmos containers anteriores e não inicia migration nem limpeza
