# Spec Delta

## Purpose

Define o comportamento de cópia cifrada e recuperação verificável do PostgreSQL global do Pick-your-Pic, separado dos bytes de mídia e dos provedores de arquivo frio.

## ADDED Requirements

### Requirement: Cópia global coerente do PostgreSQL
O sistema SHALL criar snapshots consistentes da base PostgreSQL da aplicação, incluindo dados e relações de todos os fotógrafos. A cópia MUST NOT ser apresentada como cópia dos bytes de mídia ou dos arquivos de segredo do host.

#### Scenario: Snapshot global concluído
- **WHEN** uma cópia é concluída
- **THEN** o recibo identifica um ponto consistente da base global e não afirma que fotos, volumes de mídia ou arquivos `.env` foram copiados

### Requirement: Repositório global cifrado e isolado
Antes de sair do host, o conteúdo da cópia SHALL ser cifrado. Repositório, identidade, raiz e chave do backup PostgreSQL SHALL permanecer separados dos usados para arquivo frio de mídia e SHALL NOT depender de credenciais do Google Workspace aposentado.

#### Scenario: Publicação cifrada
- **WHEN** dados da cópia são enviados ao destino configurado
- **THEN** o payload do dump não sai em claro e falhas de configuração ou de autorização não expõem dump, chave ou segredo

### Requirement: Estado de cópia validado
O sistema SHALL distinguir cópia em execução, concluída, validada, falha e estado desconhecido. Somente uma cópia com evidência íntegra SHALL ser apresentada como validada ou elegível para retenção.

#### Scenario: Resultado remoto incerto
- **WHEN** o processo termina sem confirmação verificável do destino ou da integridade
- **THEN** o estado permanece desconhecido ou indisponível e a cópia não é tratada como validada

### Requirement: Recuperação global isolada
O sistema SHALL restaurar uma cópia em alvo isolado e verificar sua integridade antes de apresentar a recuperação como validada. A recuperação MUST NOT substituir automaticamente o banco ativo.

#### Scenario: Restauração isolada aprovada
- **WHEN** uma cópia selecionada é restaurada e a verificação definida passa
- **THEN** o resultado registra o alvo isolado, a cópia de origem e a evidência de verificação sem modificar o banco ativo

### Requirement: Promoção para produção protegida
Substituir ou promover o banco global de produção SHALL exigir inventário atualizado, plano de impacto/rollback e autorização operacional específica, separados da ação de iniciar ou validar uma cópia.

#### Scenario: Promoção sem gate operacional
- **WHEN** uma recuperação validada ainda não tem autorização específica de produção
- **THEN** o sistema preserva o banco ativo e mantém a recuperação isolada para revisão

### Requirement: Retenção sem descarte prematuro
O sistema SHALL preservar ao menos a cópia global mais recente validada e MUST NOT remover cópias automaticamente antes de haver política de retenção aprovada e configurada.

#### Scenario: Política ausente ou inválida
- **WHEN** a política de retenção não está configurada ou não pode ser verificada
- **THEN** nenhuma cópia é removida automaticamente e o estado informa a limitação

### Requirement: Separação por identidade de provider de mídia
O backup e a restauração PostgreSQL SHALL preservar referências e metadados de mídia, incluindo a identidade de provider presente no catálogo, sem migrar, converter ou excluir objetos remotos. Drive legado permanece no Drive; novos objetos Rclone de mídia têm identidade explícita conforme o contrato de armazenamento de mídia.

#### Scenario: Restauração do catálogo com mídia em providers distintos
- **WHEN** a base global é restaurada e contém referências a objetos Drive existentes e objetos Rclone novos
- **THEN** as referências mantêm suas identidades originais e nenhum objeto remoto é movido, convertido ou excluído pela recuperação do banco

### Requirement: Retomada controlada após restauração
A restauração global MUST NOT reproduzir automaticamente mensagens ou efeitos externos. Workers SHALL permanecer pausados até que filas e operações duráveis afetadas sejam reconciliadas.

#### Scenario: Fila não incluída na cópia
- **WHEN** o PostgreSQL é restaurado sem o estado Redis correspondente
- **THEN** a aplicação não reexecuta operações de mídia ou cobrança e exige reconciliação antes de liberar workers

### Requirement: Agendamento diário protegido e desligado por padrão
O worker existente SHALL tentar uma cópia global no máximo uma vez por data UTC, somente depois das tarefas/filas de maior prioridade. O agendamento MUST permanecer desabilitado salvo configuração explícita `GLOBAL_POSTGRESQL_BACKUP_ENABLED=true`. A reivindicação SHALL ser protegida por chave única por data e advisory lock de sessão PostgreSQL; uma execução interrompida ou com resultado remoto incerto MUST ser registrada como `unknown` e não repetida na mesma data.

#### Scenario: Configuração ausente ou desligada
- **WHEN** `GLOBAL_POSTGRESQL_BACKUP_ENABLED` estiver ausente ou não for `true`
- **THEN** o worker não reivindica uma execução, não chama Restic/Rclone e não grava um recibo

#### Scenario: Workers concorrentes no mesmo dia
- **WHEN** mais de um worker chega à etapa diária ao mesmo tempo
- **THEN** somente um adquire o advisory lock e reivindica a data; os demais não iniciam uma segunda cópia

#### Scenario: Execução interrompida ou incerta
- **WHEN** uma linha diária permanecer `running` após a retomada do lock, ou uma cópia iniciada não produzir recibo validado
- **THEN** o estado passa a `unknown`, erros permanecem sanitizados e não há nova tentativa automática nesse dia

#### Scenario: Worker tem trabalho prioritário
- **WHEN** uma fila/tarefa existente do worker indica trabalho
- **THEN** a tentativa diária permanece como última operação de menor prioridade no ciclo
