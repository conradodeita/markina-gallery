## Purpose

Enviar notificações transacionais de pagamento por WhatsApp de forma privada, rastreável e controlada pelo fotógrafo, sem tornar o canal uma ferramenta de marketing.

## ADDED Requirements

### Requirement: Aviso de comunicação ao fotógrafo

O sistema SHALL solicitar o envio de uma notificação WhatsApp ao fotógrafo quando um cliente comunicar pagamento, sem incluir segredo, dados bancários, imagens ou URLs públicas na mensagem.

#### Scenario: Comunicação recebida

- **WHEN** o cliente comunica pagamento de um pedido válido
- **THEN** o sistema cria uma única solicitação de notificação para o fotógrafo contendo referência suficiente para revisão no painel administrativo

#### Scenario: Falha transitória de entrega

- **WHEN** o provedor WhatsApp informa falha transitória
- **THEN** o sistema registra a tentativa e agenda nova entrega sem duplicar a comunicação de pagamento ou expor o conteúdo em logs

### Requirement: Mensagem personalizada após decisão

O sistema SHALL permitir ao fotógrafo configurar no painel um texto controlado para a resposta de confirmação de pagamento e usar esse texto somente após uma decisão manual válida.

#### Scenario: Confirmação comunicada ao cliente

- **WHEN** o fotógrafo confirma o pagamento
- **THEN** o sistema envia ao telefone verificado do cliente uma mensagem de confirmação derivada do texto configurado e registra o resultado da entrega

#### Scenario: Recusa comunicada ao cliente

- **WHEN** o fotógrafo recusa a comunicação de pagamento
- **THEN** o sistema envia a mensagem de status apropriada sem confirmar pagamento e registra o resultado da entrega

### Requirement: Privacidade e controle de envio

O sistema SHALL limitar notificações de pagamento aos telefones verificados do cliente e do fotógrafo, manter credenciais do provedor fora do repositório e impedir reenvios automáticos após limite operacional configurado.

#### Scenario: Destino não autorizado

- **WHEN** uma tentativa de notificação usa telefone que não pertence ao cliente ou fotógrafo relacionado
- **THEN** o sistema bloqueia o envio e registra a falha sem divulgar o conteúdo da mensagem
