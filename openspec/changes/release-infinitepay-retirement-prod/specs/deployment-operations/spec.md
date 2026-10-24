# Spec Delta

## ADDED Requirements

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
