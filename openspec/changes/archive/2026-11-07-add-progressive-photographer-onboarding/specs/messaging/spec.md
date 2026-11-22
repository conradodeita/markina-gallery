# Spec Delta

## ADDED Requirements

### Requirement: Personalização de WhatsApp condicionada à conexão própria

A central Notificações SHALL explicar que conectar WhatsApp em Configurações permite personalizar as mensagens enviadas aos clientes. Sem conexão operacional do próprio tenant, a UI MUST bloquear controles de texto/ativação WhatsApp e apontar Configurações. Push SHALL permanecer configurável independentemente de WhatsApp. A UI MUST NOT mencionar o nome técnico do provedor.

#### Scenario: Canal ausente ou indisponível
- **WHEN** tenant sem canal operacional abre Notificações ou tenta editar WhatsApp por API
- **THEN** vê a orientação e controles bloqueados, e a API recusa a alteração sem afetar push ou dados existentes

#### Scenario: Outro tenant conectado
- **WHEN** apenas A possui WhatsApp conectado e B consulta ou altera suas mensagens
- **THEN** a conexão de A não libera B e as configurações de A permanecem preservadas

#### Scenario: Push sem WhatsApp
- **WHEN** tenant sem WhatsApp altera somente textos ou preferência push
- **THEN** a alteração é salva sem exigir canal WhatsApp e segue gates próprios de Web Push

### Requirement: Bloqueio de alterações WhatsApp no servidor

Sem conexão operacional do próprio tenant, o servidor MUST recusar alterações de texto ou habilitação WhatsApp, inclusive nas rotas legadas, sem mudar templates, versão ou filas. Campos WhatsApp inalterados em um salvamento de push MUST ser aceitos. A verificação SHALL consultar somente a conexão do tenant autenticado, sem commit parcial de outras alterações.

#### Scenario: Tentativa direta de alterar mensagem sem canal
- **WHEN** tenant sem canal operacional envia alteração de texto WhatsApp junto com alterações push
- **THEN** o servidor recusa o conjunto antes de persistir mudanças e permite novo salvamento apenas de push com WhatsApp inalterado

### Requirement: WhatsApp próprio por fotógrafo SaaS

Cada tenant fotógrafo SHALL iniciar autoconfiguração em Configurações e parear seu próprio número no adaptador de WhatsApp. O servidor SHALL criar instância isolada idempotente e guardar credenciais/webhook em armazenamento protegido, sem exposição no frontend ou tabelas comuns. Estado e entregas SHALL ser vinculados ao tenant. Canal de outro tenant MUST NOT satisfazer o gate de upload ou enviar mensagens em seu nome.

#### Scenario: Dois fotógrafos configuram seus números
- **WHEN** tenants A e B pareiam instâncias distintas no mesmo ambiente
- **THEN** cada um vê apenas o estado próprio e as notificações de seus clientes saem pela instância correspondente

#### Scenario: Canal de outro tenant está pronto
- **WHEN** A está pronto e B ainda não pareou seu número
- **THEN** B permanece pendente para upload e nenhuma fila de B usa o canal de A

#### Scenario: Canal legado existente
- **WHEN** o schema e o transporte são atualizados
- **THEN** o vínculo do canal existente e as mensagens pendentes permanecem preservados, sem criação de sessão ou pareamento implícito para outros tenants

### Requirement: Preservação do canal legado durante expansão

A migração SHALL preservar número, instância, segredo, webhook e mensagens em trânsito do canal legado sem reatribuição automática. Uma falha de migração MUST impedir habilitar novos canais sem afetar o canal operacional atual.

#### Scenario: Migração interrompida
- **WHEN** o esquema de canais por tenant não pode ser confirmado
- **THEN** o canal legado permanece vinculado ao proprietário e nenhuma instância de outro tenant assume sua identidade
