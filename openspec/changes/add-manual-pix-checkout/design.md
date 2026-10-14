## Context

O schema já contém seleção por foto, pedidos, itens de pedido e um estado financeiro pendente, porém ainda não há contrato nem fluxo que crie um pedido comercial a partir da seleção. A confirmação e as notificações posteriores são tratadas pela change `add-payment-confirmation-notifications`.

## Goals / Non-Goals

**Goals:**

- Criar um fluxo transacional que transforme somente a seleção autorizada em pedido pendente com snapshots imutáveis.
- Centralizar cálculo de faixas no servidor, usando centavos inteiros e regras validadas.
- Isolar instruções PIX por ambiente e por pedido, sem depender de provedor de pagamento.

**Non-Goals:**

- Confirmar, conciliar ou validar PIX automaticamente.
- Aceitar comprovantes, anexos, cartão, Infinity Pay ou webhook.
- Alterar pedidos confirmados, dados de outra cliente ou regras históricas.

## Decisions

### Checkout usa snapshot transacional

O checkout validará autorização, prazo, elegibilidade e preços em uma transação, gravando itens e valores no pedido. A regra corrente não será consultada para recalcular pedidos existentes. Essa decisão preserva auditoria e permite mudanças futuras de preço sem reescrever histórico.

Alternativa descartada: calcular o total somente no frontend ou derivá-lo novamente de regras atuais. Ambas permitiriam divergência ou alteração retroativa.

### Faixas são regras explícitas em centavos

Cada faixa terá limites de quantidade e preço unitário inteiros, com validação de sobreposição e lacuna. O backend calculará a faixa do carrinho e o painel exibirá a simulação e o alerta de salto comercial.

Alternativa descartada: fórmulas livres ou valores monetários de ponto flutuante, que aumentam risco de ambiguidade e arredondamento.

### PIX manual é uma instrução, não uma transação externa

As instruções de PIX serão guardadas na configuração protegida do servidor ou em configuração administrativa estruturada, e associadas ao pedido apenas como snapshot de apresentação. O pagamento permanece `pending` até a decisão explícita prevista na change subsequente.

Alternativa descartada: chamar banco ou provedor de PIX neste fluxo. Isso introduziria credenciais, webhooks e conciliação fora do escopo.

## Risks / Trade-offs

- [Dois checkouts simultâneos] → revalidar fotos elegíveis e usar constraints/transação para impedir item duplicado no mesmo pedido.
- [Regra de faixa comercial inválida] → validar limites, preço e efeito de salto antes da persistência.
- [Dados de PIX acessados por outra cliente] → derivar pedido e instruções somente da sessão autenticada e retornar resposta neutra para acesso negado.
- [Mudança de instrução após checkout] → preservar o snapshot exibido ao pedido, sem reescrever o histórico.

## Migration Plan

1. Adicionar tabelas e colunas de regra de preço, snapshots comerciais e instrução PIX com migration aditiva e downgrade correspondente.
2. Publicar cálculo, seleção e checkout com testes de isolamento e idempotência.
3. Aplicar a migration em homologação somente com dados sintéticos e validar um pedido pendente.
4. Em caso de rollback, interromper novas criações antes de reverter a migration; pedidos existentes não serão apagados automaticamente.
