## Purpose

Avisar a cliente quando o fotógrafo disponibiliza o álbum final de um pedido, usando os mesmos controles, canais e garantias da central de Notificações existente.

## ADDED Requirements

### Requirement: Evento configurável de fotos disponíveis

A central Notificações SHALL incluir o evento "Fotos disponíveis", destinado somente à cliente proprietária do pedido, com interruptores independentes de WhatsApp/push, textos editáveis, título push, prévias, limites e variáveis controladas iguais aos eventos existentes. O evento SHALL iniciar com os padrões de ativação da central, respeitando disponibilidade do transporte e adesão por dispositivo; alterações não SHALL modificar os seis eventos anteriores.

#### Scenario: Configuração na central
- **WHEN** o fotógrafo abre Notificações após a atualização
- **THEN** encontra "Fotos disponíveis" para a cliente, com WhatsApp/push e edição dos textos, junto dos eventos anteriores preservados

#### Scenario: Somente um canal habilitado
- **WHEN** o fotógrafo clica em Enviar com somente push habilitado para o evento
- **THEN** somente dispositivos ativos autorizados da cliente recebem tentativas push, sem WhatsApp

### Requirement: Enviar disponibiliza e agenda atomicamente

Ao clicar em `Enviar`, o sistema SHALL persistir o álbum e evento durável na mesma transação, somente para pedido confirmado. Digitação, carregamento, remoção e migration SHALL NOT notificar. Nova URL SHALL gerar revisão; replay ou reenvio da URL vigente SHALL NOT duplicar. Remoção seguida de nova disponibilização SHALL criar revisão nova. Avisar novamente SHALL exigir ação separada `Reenviar aviso`.

#### Scenario: Primeiro envio
- **WHEN** o fotógrafo envia pela primeira vez um link válido para pedido com pagamento confirmado
- **THEN** a entrega é persistida e os canais habilitados são agendados para a cliente daquele pedido

#### Scenario: Duplo clique ou repetição de requisição
- **WHEN** a mesma operação é repetida ou o mesmo link vigente é enviado novamente
- **THEN** permanece uma única revisão com entregas deduplicadas por destinatário, canal e dispositivo

#### Scenario: Rollback ou remoção
- **WHEN** a gravação do álbum falha ou o fotógrafo remove um link
- **THEN** nenhum novo aviso de fotos disponíveis é enviado, e a falha de gravação mantém a entrega anterior

### Requirement: Destino privado e aviso atual

O aviso SHALL direcionar a cliente a Compras, e push SHALL abrir o pedido autenticado; o URL externo SHALL permanecer no pedido, nunca em mensagem ou tela bloqueada. Antes de envio/retentativa, o sistema SHALL revalidar proprietário, pagamento, link e revisão. Remoção/substituição do link ou correção financeira SHALL cancelar permanentemente avisos antigos; nova confirmação SHALL NOT reativá-los. Expiração/remoção do acervo SHALL NOT invalidar entrega de pedido confirmado.

#### Scenario: Acesso pela notificação
- **WHEN** a cliente toca no push de fotos disponíveis
- **THEN** abre Compras no contexto do próprio pedido, com autenticação quando necessária e botão para o álbum vigente

#### Scenario: Link removido antes do processamento
- **WHEN** um aviso está pendente e o fotógrafo remove ou substitui o link
- **THEN** o worker não inicia nova tentativa da revisão anterior; uma mensagem já aceita pelo provedor não é prometida como revogada

#### Scenario: Galeria expirada ou removida
- **WHEN** a cliente ainda possui o pedido confirmado com link e o acervo operacional já expirou ou foi removido
- **THEN** a entrega pode ser notificada e consultada com autorização pela propriedade do pedido

#### Scenario: Pagamento corrigido e confirmado novamente antes do worker
- **WHEN** existe aviso pendente, o pagamento volta à revisão e é confirmado novamente antes do processamento
- **THEN** o worker cancela o aviso da revisão anterior mesmo que o pagamento já esteja confirmado; novo aviso de entrega exige ação explícita do fotógrafo

### Requirement: Reenvio deliberado do aviso de entrega

O fotógrafo SHALL confirmar `Reenviar aviso` para pedido pago com link vigente. A ação SHALL preservar link/itens/pagamento e usar a configuração atual. Cada ação confirmada distinta SHALL criar aviso novo; clique duplo, replay e retentativa da mesma ação SHALL NOT duplicar. O sistema MUST NOT enviar rascunho de URL diferente do link salvo.

#### Scenario: Fotos adicionadas ao mesmo álbum
- **WHEN** o fotógrafo acrescenta fotos no Google Photos e confirma Reenviar aviso no pedido
- **THEN** o sistema agenda um novo aviso para os canais habilitados sem exigir alteração ou remoção do link cadastrado

#### Scenario: Repetição da mesma ação
- **WHEN** a requisição de um reenvio confirmado é repetida com o mesmo identificador de operação
- **THEN** o sistema retorna o resultado da operação existente sem criar outro aviso

#### Scenario: Link alterado durante reenvio
- **WHEN** o link ou sua revisão muda depois que o formulário de reenvio foi carregado
- **THEN** o sistema rejeita a ação desatualizada e solicita atualização, sem enviar aviso sobre outro álbum

#### Scenario: Reenvio sem entrega elegível
- **WHEN** não há link salvo ou o pagamento não está confirmado
- **THEN** Reenviar aviso fica indisponível e o backend rejeita a operação sem evento externo

### Requirement: Falha do canal não desfaz disponibilização

As tentativas SHALL usar os workers, limites, expiração, snapshots de texto e tratamento de erros existentes, sem transporte síncrono no formulário. Falhas SHALL NOT retirar o botão verde nem alterar pagamento. A resposta administrativa SHALL distinguir link disponibilizado de aviso agendado e SHALL NOT afirmar entrega ou leitura humana. Canais desligados SHALL NOT produzir envios; reativá-los SHALL NOT reproduzir eventos passados.

#### Scenario: Provedor falha
- **WHEN** WhatsApp falha após disponibilização persistida
- **THEN** o álbum permanece disponível, push segue independente e a falha é tratada no mecanismo técnico existente sem histórico no card

#### Scenario: Todos os canais desligados
- **WHEN** o fotógrafo clica em Enviar com ambos os canais desligados
- **THEN** o álbum fica disponível, nenhum transporte é solicitado e a interface informa que os avisos estão desativados

#### Scenario: Ativação posterior
- **WHEN** um canal é ligado após disponibilizações anteriores
- **THEN** somente novas disponibilizações ou reenvios explicitamente confirmados seguem a configuração, sem envio retroativo automático
