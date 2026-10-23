# Spec Delta

## ADDED Requirements

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
