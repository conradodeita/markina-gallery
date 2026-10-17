# Proposal

## Why

O aviso de novas fotos privadas chega ao cliente, mas não informa um endereço clicável para retornar à galeria que originou a pasta. Incluir o link da galeria-mãe torna a mensagem acionável sem ampliar permissões: o endereço continua exigindo a autenticação e o vínculo já existentes.

## What Changes

- Disponibilizar `{{link_galeria}}` somente no template WhatsApp do evento `private_photos_ready`, com URL HTTPS criada no servidor a partir da galeria-mãe associada ao evento.
- Definir o texto padrão como `Essa mensagem é automática! Novas fotos disponíveis na sua galeria. Acesso no link: {{link_galeria}}.` e mostrar a variável na central administrativa.
- Atualizar para o novo padrão somente configurações que ainda contenham o texto padrão anterior; preservar mensagens personalizadas.
- Cancelar a entrega WhatsApp quando a origem ou o hostname canônico não puderem ser validados, preservando push e demais canais.

## Capabilities

### New Capabilities

- `messaging/private-photo-gallery-links`: geração e uso seguro do link da galeria-mãe em avisos WhatsApp de novas fotos privadas.

### Modified Capabilities

Nenhuma spec principal de messaging foi consolidada; o requisito será introduzido como capacidade própria e focada.

## Impact

Afeta o contrato de mensagens e templates, a montagem do snapshot WhatsApp de `private_photos_ready`, a validação de URLs de galeria, a configuração administrativa e testes de backend. Uma migration de dados atualiza somente o template padrão antigo exato, sem alterar mensagens personalizadas, OTP, permissões, links de push ou entregas já persistidas.
