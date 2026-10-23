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

## Seguimento operacional autorizado em 22/10/2026

Após merge262/266 e recusa esperada do CI789 no gate protegido, o proprietário autorizou preparar a operação0086 e escolheu guardar no PC o backup cifrado da chave mestra. Preparar inventário, ensaios de restore e utilitário manual de geração/custódia, sem relaxar workflow0084. O preparador não publica nem reinicia aplicação. Execução com segredo exige participação do proprietário em terminal oculto; dados financeiros e pagamentos reais permanecem fora desta preparação. Evidência em release-preparation-20261022.md.

Escopo inicial antes do merge: API/web, cliente HTTP, confirmação e callback, projeções, testes e migration aditiva0086 após0085. Sem operação real, chave, Oracle, merge ou publicação naquela fase. O proprietário manterá PIX do checkout desligado até publicação. PR266 então verde e isolado; implementação no mesmo PR262, à época draft. O seguimento acima e release-preparation-20261022.md registram o estado posterior.
