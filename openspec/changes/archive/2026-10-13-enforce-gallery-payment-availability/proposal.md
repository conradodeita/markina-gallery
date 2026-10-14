# Proposal

## Why

Uma galeria com `Pagamento obrigatório?` pode hoje salvar suas regras comerciais sem oferecer um meio utilizável; a contradição aparece apenas quando a cliente tenta pagar. O proprietário esclareceu em 13/10/2026 que a exigência depende da jornada da galeria: quando ligada, deve haver pelo menos um meio efetivo da própria conta; quando desligada, a seleção termina sem cobrança.

## What Changes

- Validar no servidor e na etapa 2 que a cobrança obrigatória possui ao menos um meio utilizável da conta do fotógrafo, com orientação para Configurações quando faltar recebimento.
- Manter PIX como opção inicial quando configurado e utilizável. Cartão continua adicional, desligado inicialmente e habilitado individualmente pelo fotógrafo na configuração InfinitePay existente.
- **BREAKING**: permitir apenas substituir um PIX já configurado mediante confirmação sensível, retirando sua remoção explícita da UI e recusando a remoção também na API. Contas sem PIX e galerias sem cobrança não passam a depender de cadastro bancário.
- Preservar a possibilidade especificada de cartão utilizável quando PIX ainda não foi configurado; não mostrar uma opção PIX sem dados válidos nem deixar a preparação automática de PIX impedir esse caminho.
- Revalidar o meio escolhido no checkout e preservar a jornada existente de `Finalizar seleção`, inclusive no carrinho misto, sem fabricar receita ou enviar dados à InfinitePay.
- Manter snapshots e reservas de cobranças já emitidas. Uma troca de configuração não reescreve pedidos antigos.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: validação da disponibilidade de pagamento na etapa comercial e conservação da finalização sem cobrança.
- `gallery-sales/global-pix-configuration`: configuração somente substituível após ativação e escolha padrão de PIX utilizável.

## Impact

Editor comercial, painel PIX, leitura autoritativa de capacidades por conta, APIs de alteração sensível, preparação e revisão do carrinho. Reutilizar os contratos de `simplify-gallery-access-modes`, `add-small-multi-photographer-pilot` e `add-infinitepay-credit-payments`; não duplicar o controle de cartão já implantado pelo PR #166.

Base investigada: `origin/develop` em `0ef80fdf912e8f9cbde730d061b69b73d46ff5aa`. A investigação é somente leitura, sem pagamento ou alteração real de configuração. Esta proposta depende de revisão humana antes de aplicação; webhook/retorno, taxas, cancelamento remoto, deploy e limpeza não fazem parte desta change.

## Review

O proprietário aprovou esta proposta após o esclarecimento da jornada condicional, respondendo “Sinal verde! Prossiga.” em 13/10/2026. O aceite autoriza aplicação e validação locais; operações reais de pagamento, deploy, limpeza, sincronização e archive conservam seus controles próprios.
