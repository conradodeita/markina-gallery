# Spec Delta

## ADDED Requirements

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
