# Proposal

## Why

O aviso de fotos disponíveis no WhatsApp atualmente diz para a cliente acessar Compras, mas não oferece um link direto. Um link de pedido enviado no contexto do subdomínio do fotógrafo deve abrir o pedido correto para uma sessão válida ou retomar esse destino depois do OTP, sem misturar pedidos de fotógrafos diferentes.

## What Changes

- Incluir no evento configurável “Fotos disponíveis” um link interno para Compras e para o pedido correspondente, usando a origem canônica do subdomínio daquele fotógrafo.
- Enquanto existir somente um fotógrafo ativo, permitir que a origem pública HTTPS configurada da aplicação funcione como hostname canônico implícito; quando houver múltiplos fotógrafos, exigir hostname canônico registrado individualmente para cada um.
- Reutilizar o link externo já salvo por pedido no card de Vendas e pagamentos como condição/origem do mesmo evento existente; permitir links de compartilhamento HTTPS de serviços externos de arquivos (Google Photos, Drive ou equivalente) e manter esse destino no botão verde “Fotos disponíveis” da compra autenticada.
- Preservar o contexto do subdomínio e o destino autorizado durante o login OTP; após validar o código, encaminhar a cliente ao pedido somente quando ele pertencer ao fotógrafo e à identidade autenticada.
- Isolar sessão, consultas e projeções de compras pelo fotógrafo do subdomínio. Hostnames, IDs de tenant ou UUIDs de pedido enviados pelo navegador não concedem autorização.
- Manter qualquer link externo do álbum fora da mensagem. `{{link_compras}}` SHALL apontar à compra da cliente no subdomínio do fotógrafo dono do pedido; depois da autenticação, a cliente usa o botão de álbum já existente para abrir o destino externo salvo naquele pedido.
- Preservar as configurações independentes de WhatsApp/push, a deduplicação e os gates de pagamento e revisão da entrega.

## Capabilities

### New Capabilities

- `messaging/order-delivery-deep-link`: incluir um destino interno seguro para o pedido do cliente nas mensagens WhatsApp de fotos disponíveis.
- `client-access/tenant-domain-routing`: resolver o tenant pelo subdomínio canônico e manter Compras no contexto desse fotógrafo.

### Modified Capabilities

- `auth`: preservar e validar o destino interno de uma compra através do OTP, vinculado ao contexto do fotógrafo e ao cliente autenticado.

## Impact

Impacta `Tenant`/hostnames e propriedade comercial por fotógrafo, sessão de cliente e OTP, rotas e projeções de Compras, template/renderização e worker do evento existente `order_delivery_ready`, validação dos links externos de álbum, links enviados pelo transporte WhatsApp e configuração de domínios/subdomínios. Requer reconciliação com a fundação de tenant e com a change `add-order-google-photos-delivery`; não inclui o link externo do álbum no WhatsApp nem envia mensagens durante testes.

Esta change depende do contrato `add-small-multi-photographer-pilot` para cadastros de cliente independentes e sessões tenant-scoped. Ela acrescenta roteamento confiável por subdomínio para Compras, sem alterar a identidade OTP nem permitir ativação operacional de fotógrafo adicional antes dos gates daquele piloto.
