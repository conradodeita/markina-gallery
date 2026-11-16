# Spec Delta

## MODIFIED Requirements

### Requirement: WhatsApp próprio por fotógrafo SaaS

Cada tenant fotógrafo SHALL iniciar autoconfiguração em Configurações e parear seu próprio número no adaptador de WhatsApp. O servidor SHALL criar instância isolada idempotente e guardar credenciais/webhook em armazenamento protegido, sem exposição no frontend ou tabelas comuns. Estado e entregas SHALL ser vinculados ao tenant. Canal de outro tenant MUST NOT satisfazer o gate de upload ou enviar mensagens em seu nome.

#### Scenario: Primeiro provisionamento pela tela de Configurações

- **WHEN** um fotógrafo SaaS autenticado, sem instância própria provisionada, informa seu número de WhatsApp em Configurações e solicita a conexão
- **THEN** o servidor cria ou recupera de forma idempotente a instância exclusiva do tenant e apresenta o estado aguardando pareamento
- **AND** a tela permite iniciar o pareamento somente após o provisionamento confirmado
- **AND** o segredo de webhook permanece cifrado no armazenamento de credenciais vinculado ao tenant e ao ambiente, sem ser retornado ao frontend nem persistido em tabelas de domínio comuns
- **AND** QR e código de pareamento não são persistidos e só ficam disponíveis pela resposta temporária de pareamento
- **AND** uma falha mantém o canal não pronto, conserva o número informado para nova tentativa e não afeta outro tenant

#### Scenario: Dois fotógrafos configuram seus números

- **WHEN** tenants A e B pareiam instâncias distintas no mesmo ambiente
- **THEN** cada um vê apenas o estado próprio e as notificações de seus clientes saem pela instância correspondente

#### Scenario: Canal de outro tenant está pronto

- **WHEN** A está pronto e B ainda não pareou seu número
- **THEN** B permanece pendente para upload e nenhuma fila de B usa o canal de A

#### Scenario: Canal legado existente

- **WHEN** o schema e o transporte são atualizados
- **THEN** o vínculo do canal existente e as mensagens pendentes permanecem preservados, sem criação de sessão ou pareamento implícito para outros tenants

## ADDED Requirements

### Requirement: Edição de número em canal já provisionado

Quando o tenant já possui canal próprio, Configurações SHALL atualizar o número esperado sem criar outra instância e SHALL manter o pareamento obrigatório para confirmar a identidade do número.

#### Scenario: Alterar número de um canal existente

- **WHEN** um fotógrafo com instância própria altera o número esperado
- **THEN** a instância existente é mantida, o estado volta para aguardando pareamento e o envio permanece bloqueado até a nova identidade estar pronta
