## Purpose

Centralizar mensagens curtas e configuráveis de eventos transacionais de galerias e pagamentos para fotógrafo e cliente, com canais independentes.

## ADDED Requirements

### Requirement: Matriz de eventos e destinatários

O sistema SHALL oferecer WhatsApp e push para os seis eventos abaixo, com dois interruptores independentes por evento: `Enviar WhatsApp` e `Enviar notificação push`. Os destinatários SHALL ser resolvidos pelo backend e não editáveis como endereços arbitrários nos templates.

| Evento | Destinatário | Unicidade |
|---|---|---|
| Primeiro login concluído por OTP em uma galeria | Admin/fotógrafo | Cliente e galeria |
| Primeira foto selecionada naquela galeria | Admin/fotógrafo | Cliente e galeria |
| Novas fotos privadas com prévias disponíveis | Clientes ativos autorizados ao lote | Lote e cliente |
| Pagamento comunicado pelo cliente | Admin/fotógrafo | Comunicação válida de pagamento |
| Pagamento confirmado pelo admin | Cliente do pedido | Decisão válida |
| Pagamento recusado pelo admin | Cliente do pedido | Decisão válida |

#### Scenario: Primeiro acesso e repetição
- **WHEN** o cliente conclui OTP e tem acesso autorizado à galeria pela primeira vez
- **THEN** gera o aviso ao admin uma vez, sem novo aviso para repetição do OTP ou sessões posteriores na mesma galeria, permitindo um aviso distinto em outra galeria

#### Scenario: Primeira seleção independente de criação
- **WHEN** o cliente seleciona sua primeira foto na galeria, mesmo que a privada já exista
- **THEN** gera um aviso ao admin, sem repetir ao desmarcar/selecionar novamente e sem disparar apenas pela criação administrativa da privada

#### Scenario: Lote de novas fotos
- **WHEN** um lote de uploads administrativos em privada encerra processamento e possui novas prévias disponíveis para um cliente autorizado
- **THEN** gera um único aviso para esse cliente, com texto padrão `Novas fotos disponíveis na sua galeria.`, sem aguardar reconhecimento facial ou ajuste opcional e sem emitir um aviso por fotografia

#### Scenario: Falha ou repetição de lote
- **WHEN** um lote não possui nenhuma nova prévia disponível, ou seus jobs já notificados são repetidos
- **THEN** não envia anúncio de novas fotos nem duplica aviso; retentativa de fotos falhas de lote já anunciado não repete esse anúncio

#### Scenario: Pagamentos isolados
- **WHEN** comunicação, confirmação ou recusa é persistida com sucesso
- **THEN** agenda os canais habilitados para o destinatário correspondente sem compartilhar pedidos com outros clientes da galeria; a correção administrativa silenciosa de decisão continua sem mensagem

### Requirement: Configuração central com textos curtos

`Notificações` SHALL substituir a listagem antiga por configuração agrupada por evento e destinatário, com títulos/corpos push, texto WhatsApp, prévia, contagem de caracteres e interruptores separados. SHALL mover os templates de pagamento de Configurações sem perder os valores salvos, explicar que alterações são globais e manter texto simples e variáveis controladas. A interface SHALL funcionar em mobile/desktop e nos dois temas, sem prometer exibição integral em todo celular.

#### Scenario: Edição global
- **WHEN** o admin salva um texto válido
- **THEN** eventos futuros usam a nova versão, sem modificar mensagens históricas, retransmitir eventos passados ou alterar um snapshot já enfileirado

#### Scenario: Canal desligado
- **WHEN** o admin desliga um canal para um evento
- **THEN** esse canal não inicia novas entregas nem retentativas pendentes desse evento, mantendo o outro canal independente; religar não reproduz o histórico descartado

#### Scenario: Migração da página
- **WHEN** o admin abre Notificações após a atualização
- **THEN** encontra a central e os textos de pagamento preservados, sem a antiga caixa de leitura; os registros técnicos e de auditoria continuam preservados e erros operacionais não são mostrados ao cliente

### Requirement: Negócio independente da entrega

Eventos e solicitações de envio SHALL ser duráveis e deduplicados por evento, destinatário e canal, com falhas e retentativas limitadas e independentes. Um resultado de transporte SHALL NOT confirmar leitura humana nem desfazer login, seleção, importação ou decisão financeira.

#### Scenario: Provedor indisponível
- **WHEN** um canal falha ou não está configurado
- **THEN** registra estado sanitizado, não bloqueia o outro canal e preserva a operação de negócio

#### Scenario: Migração sem spam
- **WHEN** a versão é publicada ou um canal é ativado
- **THEN** não envia notificações de eventos anteriores nem recria envios já existentes em outboxes legadas
