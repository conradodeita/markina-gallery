# Why

O proprietário aprovou cartão e PIX no mesmo checkout InfinitePay, preservando PIX manual, e decidiu que pagamentos externos ainda não concluídos pertencem ao Carrinho. Abrir o gateway não equivale a compra efetivada. O contrato anterior força cartão e rejeita PIX na confirmação; mudar somente a preferência no app não resolve.

# What Changes

- Novos links oferecem credit_card e pix, single_payment true. Retomar usa a mesma URL, sem gerar cobrança alternativa PIX manual para fotos reservadas.
- Confirmar ambos os métodos somente após payment_check no servidor; webhook de pagamento é candidato não confiável, nunca prova financeira por si. Persistir método verificado e meios permitidos por compra, preservando links antigos exclusivos de cartão.
- Pendências externas aparecem no Carrinho com fotos e retomada; Compras conserva PIX informado/recusado, confirmações/entregas e conferência financeira excepcional.
- Esvaziar pendência externa oculta a intenção no Carrinho sem cancelar link, liberar reserva ou apagar snapshots. Retorno tardio continua conciliável e pode gerar ocorrência visível.
- Orientar habilitar cartão e PIX na InfinitePay; PIX manual continua separado e normal antes da emissão externa.

# Capabilities

## New Capabilities
- `gallery-sales/infinitepay-mixed-checkout-cart`: checkout misto e projeção no Carrinho.

## Modified Capabilities
- Contrato de cartão exclusivo e projeção de awaiting_payment em Compras substituídos por decisão explícita do proprietário. Specs consolidadas só após revisão humana.

# Impact

API/web, cliente HTTP, confirmação e callback, projeções, testes e migration aditiva0086 após0085. Nenhuma operação real, chave, Oracle, merge ou publicação. O proprietário manterá PIX do checkout desligado até publicação. PR266 já verde permanece isolado; alteração no mesmo PR262, ainda draft.
