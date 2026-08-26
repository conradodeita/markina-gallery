## Context

Veja `proposal.md` e as especificações desta mudança. O sistema atual possui pedidos com estado de pagamento e um adaptador WhatsApp em sandbox usado apenas pela autenticação; não há envio real, fila de notificações nem fluxo de revisão de pagamento.

## Goals / Non-Goals

**Goals:**
- Persistir a comunicação de pagamento e a decisão manual de forma idempotente e auditável.
- Enfileirar notificações transacionais em vez de enviar dentro da requisição HTTP.
- Permitir textos configuráveis com variáveis controladas, sem HTML nem conteúdo de comprovante.

**Non-Goals:**
- Conciliar PIX, validar comprovantes, processar cartão ou confirmar pagamentos automaticamente.
- Enviar campanhas, mensagens livres em massa ou anexos.
- Reutilizar credenciais de homologação em produção ou registrar tokens, corpos de mensagens ou dados bancários em logs.

## Decisions

### Comunicação não equivale a pagamento

Uma comunicação cria estado pendente de revisão, separado do estado financeiro confirmado. A confirmação só é efetuada pela ação autenticada do fotógrafo; isso evita que uma declaração do cliente altere receita, entrega ou histórico por engano.

### Caixa de saída e worker idempotente

Cada evento gera registro de caixa de saída com chave idempotente, estado, contador de tentativas e erro sanitizado. Um worker envia ao adaptador WhatsApp, em vez de a API depender da disponibilidade do provedor. Requisições repetidas ou novas tentativas não poderão gerar confirmações financeiras ou notificações duplicadas.

### Templates controlados

O fotógrafo configura textos curtos com variáveis permitidas, como nome do cliente, número do pedido e nome da galeria. O sistema valida e renderiza essas variáveis no servidor; HTML, URLs públicas de mídia e interpolação arbitrária não são permitidos.

### Integração isolada por ambiente

O adaptador WhatsApp será uma porta configurada apenas por segredos do ambiente. A homologação usará dados sintéticos e poderá manter sandbox até que credenciais próprias sejam aprovadas. A ativação real exigirá inventário e aprovação operacional separados.

## Risks / Trade-offs

- [Falha ou duplicação no provedor] → caixa de saída idempotente, tentativas limitadas e painel com estado de entrega.
- [Mensagem enviada ao destino errado] → derivar destinatário somente da identidade verificada vinculada ao pedido e validar antes da fila.
- [Confirmação incorreta] → decisão manual imutável, auditoria e apresentação clara do estado pendente.
- [Indisponibilidade do WhatsApp] → confirmação permanece registrada; o fotógrafo pode reenviar dentro do limite configurado.

## Migration Plan

Criar migration aditiva para comunicações, decisões, configurações de template e caixa de saída. Validar o fluxo inteiro com adaptador sintético, aplicar em homologação apenas com dados sintéticos e credenciais próprias, e habilitar o provedor real somente após aprovação explícita do inventário de impacto zero.
