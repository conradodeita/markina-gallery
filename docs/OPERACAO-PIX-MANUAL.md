# Operação de PIX manual

## Escopo

O checkout de uma galeria privada cria somente um pedido com status `pending`.
Ele não consulta bancos, não envia comprovantes, não possui webhook e não
confirma pagamento. A confirmação é uma decisão operacional explícita prevista
no fluxo de confirmação manual e nas notificações posteriores.

## Configuração por galeria

1. Acesse **Galerias**, abra a galeria privada da cliente e selecione
   **Preço e PIX manual**.
2. Defina faixas contíguas a partir de uma foto. Os valores são centavos
   inteiros no servidor, embora o painel os apresente em reais.
3. Revise o aviso quando uma nova faixa diminui o preço total ao aumentar a
   quantidade. Salve esse tipo de regra somente após confirmação consciente.
4. Preencha somente as instruções que a cliente deve ver: copia-e-cola, payload
   de QR Code e uma orientação curta.
5. Salve e confira um pedido sintético pendente em **Pedidos**.

As instruções são congeladas no pedido. Alterar a configuração depois do
checkout não altera pedidos já criados.

## Segurança e dados

- Nunca versionar, enviar por issue, registrar em logs ou colocar em `.env`
  chaves bancárias, tokens, credenciais de provedores ou dados reais de
  clientes.
- As instruções PIX são exibidas somente à cliente proprietária de um pedido
  pendente e ao administrador autorizado. Elas não são uma credencial de
  infraestrutura.
- Homologação usa somente dados sintéticos. Não testar com dados de crianças
  ou informações bancárias reais.

## Conferência e confirmação manual

O painel **Pedidos** continua sendo uma consulta dos snapshots congelados. A
cliente usa **Já fiz o PIX** para criar uma comunicação pendente, sem confirmar
o pedido. O fotógrafo confronta o pagamento com a conta bancária pelos seus
procedimentos internos e registra a primeira decisão no painel **Pagamentos**.
Confirmação e recusa enfileiram uma resposta transacional; falha do WhatsApp não
altera a decisão financeira. Consulte
[`OPERACAO-NOTIFICACOES-PAGAMENTO.md`](OPERACAO-NOTIFICACOES-PAGAMENTO.md).

## Rollback

1. Interrompa novas configurações e checkouts antes de reverter código ou
   migration.
2. Não apague pedidos pendentes nem snapshots comerciais para "limpar" a
   situação. Eles são registro operacional.
3. Um rollback de aplicação pode ocultar a superfície nova, mas não deve
   alterar pedidos existentes. Reverter a migration exige avaliação humana
   porque remove estruturas que podem conter histórico.
4. Em homologação, siga o procedimento de deploy e rollback aprovado; não use
   comandos destrutivos de banco, `git reset --hard`, `git clean` ou deploy
   manual fora do fluxo autorizado.
