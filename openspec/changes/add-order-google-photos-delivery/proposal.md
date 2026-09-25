## Why

O fotógrafo entrega as fotos finais por álbuns criados manualmente no Google Photos. O histórico de mensagens no card administrativo do pedido ocupa o espaço que ele precisa para cadastrar essa entrega, enquanto a cliente precisa acessar o álbum diretamente em Compras, junto das prévias que comprou.

## What Changes

- Substituir, no card administrativo de cada pedido em Vendas e pagamentos, o texto da mensagem e os estados/tentativas/reenvio por um campo "Link do álbum no Google Photos", com botão "Enviar", edição e remoção. Digitar não disponibiliza nem notifica; Enviar persiste o link e agenda o aviso.
- Exibir por pedido em Compras um botão verde "Fotos disponíveis" quando houver link salvo e pagamento confirmado; nos demais casos, exibir botão cinza desabilitado "Fotos indisponíveis". Preservar prévias, ampliação, nomes, valores e situação financeira.
- Abrir o álbum informado pelo fotógrafo em nova aba, com link restrito ao cliente proprietário do pedido na aplicação. A expiração da seleção não remove a entrega.
- Manter links independentes entre pedidos, mesmo dentro do mesmo PIX. Disponibilizar ou remover link não confirma, recusa nem corrige pagamento.
- Exigir pagamento confirmado para Enviar ou Reenviar aviso. Se uma correção devolver o pagamento à revisão, preservar o link para o fotógrafo e suspender sua exposição à cliente até nova confirmação, invalidando avisos pendentes da entrega anterior.
- Oferecer "Reenviar aviso" para notificar novamente sobre o mesmo álbum, por exemplo após inclusão de fotos no Google Photos. Cada ação deliberada gera um novo aviso, enquanto duplo clique ou repetição da mesma requisição não duplica o envio.
- Não criar backup, exportação ou arquivo paralelo do histórico visual removido. Filas compartilhadas de comunicação e auditoria operacional seguem seus contratos existentes; esta proposta não inclui expurgo de banco nem desativação de notificações de pagamento.
- Acrescentar o evento "Fotos disponíveis" para a cliente em Notificações, com interruptores independentes de WhatsApp/push, textos editáveis e prévias iguais aos eventos existentes. Enviar disponibiliza o álbum e agenda somente os canais habilitados. Remover o link é silencioso; falha do aviso não retira o álbum de Compras.
- Esta entrega usa verde/cinza, substituindo neste escopo a previsão futura de cartões vermelho/amarelo do mandato/roadmap. A comunicação de entrega passa a usar a central existente, conforme complemento explícito do proprietário em 25/09/2026.

## Capabilities

### New Capabilities

- `gallery-sales/order-album-delivery`: cadastro administrativo do link por pedido e acesso autenticado ao álbum pela cliente, substituindo o histórico visual de mensagens.
- `messaging/order-delivery-notification`: aviso de entrega por pedido integrado à configuração e às filas transacionais existentes.

### Modified Capabilities

Nenhuma spec principal descreve hoje o cadastro do álbum. A capacidade nova complementa o histórico privado e a operação de pedidos sem reescrever requisitos já consolidados.

## Impact

Modelo `SaleOrder`, migration aditiva, endpoint administrativo de entrega e projeções de Vendas e pagamentos/Compras; matriz, configuração, eventos e workers de notificações; componentes Next.js do pedido e estilos acessíveis; testes de isolamento, URL, persistência, deduplicação, canais, estados e regressão financeira. Sem integração/API Google Photos, validação remota do álbum, envio real, secrets ou deploy nesta etapa.

Relaciona-se às changes `client-gallery-covers-and-payment-review`, `unified-client-cart-and-pix`, `delete-gallery-assets-preserve-history` e `configurable-push-and-whatsapp-notifications`. A substituição visual não elimina decisões financeiras, histórico comercial ou mecanismos internos de comunicação. Em 25/09/2026, após revisão dos pontos em aberto, o proprietário aceitou as recomendações de reenvio explícito e entrega somente após pagamento confirmado. Esses refinamentos estão incorporados ao planejamento e à implementação autorizada por “Aplique a change”. Após implementação autorizada, push + PR e parada para confirmação humana do CI, conforme o processo combinado.
