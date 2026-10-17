# Proposal

## Why

A finalização de uploads em pastas privadas precisa produzir o evento configurável `private_photos_ready` quando as prévias estiverem prontas e disponíveis, sem depender do fluxo de publicação da Galeria pública. Além disso, Vendas e pagamentos exibe um resumo de falhas derivado de uma projeção legada, e a Visão Geral combina contagens com escopos diferentes, confundindo itens de preparação com trabalho real.

## What Changes

- Disparar `Novas fotos privadas` ao finalizar um lote de upload numa pasta privada (pasta restrita a clientes) quando ao menos uma prévia protegida estiver pronta e disponível; respeitar os interruptores independentes de WhatsApp e push, autorização atual e deduplicação por lote/cliente. Upload de pasta pública não dispara este evento.
- Remover o KPI agregado `Falhas de mensagem` de Vendas e pagamentos, cuja projeção de compatibilidade pode representar canal desativado ou estado terminal como falha. Preservar estados e ações de recuperação por pedido quando houver falha real.
- Corrigir o card da Visão Geral para contar pastas públicas e privadas de conteúdo com ao menos um job de foto em andamento; o detalhe passa a somar todas as fotos cadastradas dentro dessas pastas. Pastas auxiliares, jobs encerrados e pastas sem job ativo não entram na contagem.

## Capabilities

### New Capabilities

- `messaging/private-photo-availability-notifications`: disparo idempotente dos avisos de novas fotos privadas no momento em que as prévias passam a estar disponíveis à cliente.

### Modified Capabilities

- `gallery-sales/payment-operations-dashboard`: remoção do KPI agregado de falhas baseado na projeção legada, preservando estados de entrega por pedido que continuem acionáveis.
- `gallery-sales/operational-gallery-interface`: definir escopo e consistência dos indicadores de pastas em preparação e trabalhos de mídia apresentados na Visão Geral.

## Impact

Backend de conclusão de uploads privados e outbox transacional; migration preservadora de registros para associar lotes duráveis a pastas restritas canônicas e permitir retentativas; endpoint administrativo de resumo; consulta e cards da página Vendas e pagamentos; painel Visão Geral; testes de backend e frontend. Não requer nova credencial, alteração de integração externa ou acesso ao servidor.
