# Proposal

## Why

Fotógrafos com carteira finita precisam entender o efeito financeiro dos uploads no próprio fluxo de envio e encontrar pacotes disponíveis de forma clara. O proprietário precisa localizar uma conta sem percorrer uma lista crescente. As interfaces devem refletir dados autorizados pelo backend e respeitar a separação entre tenants.

## What Changes

- Mostrar no fluxo da pasta o saldo disponível e as reservas durante o envio, atualizando o estado após cada resultado confirmado pelo servidor: consumo, liberação ou reconciliação pendente.
- Substituir o seletor simples do proprietário por busca digitável com sugestões enquanto a pessoa escreve, identificando tenants pelo nome do fotógrafo e pelo e-mail administrativo. A busca não terá botão separado e permanecerá restrita ao proprietário.
- Acrescentar consulta explícita Todos, Ordem alfabética e Mais recentes, com estado inicial limpo e resultados paginados no servidor. A busca aceita o nome informado no cadastro quando persistido e o e-mail administrativo; contas legadas sem nome continuam pesquisáveis por e-mail, sem inferência nem backfill.
- Exibir o catálogo de pacotes ativos logo abaixo da carteira do fotógrafo aprovado, em cards responsivos, elegantes e dinâmicos, com dados do servidor. Clicar no card ou em seu botão de compra abre o checkout transparente Mercado Pago já usado pela plataforma, sem saída para uma página hospedada externa.
- Para compra de créditos, usar por padrão a conta Mercado Pago configurada pelo proprietário para receber pedidos de fotografias. Mercado Pago é o único provedor habilitado neste fluxo; o PIX interno do sistema não é oferecido.
- Manter a API como autoridade de reserva, captura, liberação, saldo e autorização; a interface não estimará nem afirmará consumo quando o resultado estiver incerto.

- Agrupar o histórico de consumo por pasta para proprietário e fotógrafo, com referência, data/hora, quantidade de fotos cobradas e total de créditos. Novos envios à mesma pasta atualizam seu resumo; a interface habitual não exibe movimentos individuais por foto; a rastreabilidade individual permanece em consultas internas autorizadas. Compras, concessões, revogações e estornos permanecem individualizados.

- Apresentar a compra de créditos em linguagem comercial clara para o fotógrafo, sem explicar mecanismos internos nem provedores que não participam da compra.

## Capabilities

### New Capabilities

- `billing/photographer-credit-experience`: apresentar carteira durante uploads, busca de fotógrafos pelo proprietário e catálogo de pacotes para fotógrafos aprovados.

### Modified Capabilities

<!-- Nenhuma spec principal existente cobre ainda esses fluxos de experiência. -->

## Impact

Frontend do upload JPEG, operações globais de créditos e área do fotógrafo; endpoint owner-only de pesquisa de tenants; nome do fotógrafo fornecido pelo cadastro aprovado em `add-photographer-signup-portal`; catálogo e seleção integrados a `add-mercadopago-credit-purchases`. A compra usa a conta do tenant associado ao proprietário global, resolvida no servidor; o tenant comprador continua sendo o fotógrafo autenticado. Não altera as ordens, credenciais, PIX ou histórico das vendas de fotografias. Os cards usam somente pacotes ativos e dados comerciais vindos do servidor, sem criar preços ou promoções.
