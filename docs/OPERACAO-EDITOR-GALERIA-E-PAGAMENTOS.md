# Operação do editor de galeria e Pagamentos

## Escopo

Este guia descreve o fluxo administrativo da Galeria pública. “Pública” é o
nome de produto da origem compartilhável: a grade continua protegida por link
opaco, OTP e regras de acesso. A publicação não cria cópias nem libera fotos em
todas as galerias privadas.

## Etapa 02 — Vendas

Configure na própria Galeria pública:

- faixas contíguas de preço e o salto comercial confirmado pelo fotógrafo;
- PIX por copia-e-cola completo ou chave simples (CPF, telefone ou e-mail),
  com nome/cidade do recebedor quando necessários, e mensagem à cliente;
- prazo de seleção e permissões de favoritos e comentários.

Os valores são enviados ao servidor em centavos inteiros. Alterações futuras
serão herdadas por privadas ainda operacionais, mas nunca reescrevem o snapshot
de um pedido já criado. A cliente comunicar que pagou não confirma o pedido: a
decisão permanece manual no painel **Pagamentos**.

## Etapa 03 — Detalhes e apresentação

A capa pode ser uma foto de conteúdo já processada ou um JPEG enviado
diretamente nesta etapa. O upload dedicado reutiliza o pipeline protegido e
fica em uma pasta técnica que não aparece na grade, nas contagens ou na
publicação de conteúdo. Enquanto a imagem estiver processando, aguarde a
atualização da opção antes de selecioná-la.

Título, posição, cor e tipografia são mostrados na prévia reativa. As
tipografias são tokens controlados, servidos por quatro arquivos WOFF2 locais;
CSS, URL ou fonte arbitrária são recusados. A organização das pastas não é
configurada aqui.

## Etapa 04 — Imagens e pastas

Escolha `individual` para navegar uma coleção por vez ou `sequential` para
exibir as coleções em sequência. Depois:

1. crie ou abra uma pasta de conteúdo;
2. envie JPEGs e acompanhe processamento, falhas e itens prontos;
3. revise o lote;
4. use **Salvar e avançar** para publicar todos os derivados concluídos na
   Galeria pública e só então abrir Clientes.

A primeira publicação muda a pasta para publicada. É permitido enviar novas
fotos à mesma pasta: o conteúdo anterior continua visível, enquanto os novos
arquivos ficam indisponíveis até uma nova publicação explícita. Repetir a
publicação é idempotente. Se algum arquivo ainda estiver processando ou tiver
falhado, o editor permanece nessa etapa e mostra as contagens. Nenhuma
referência de galeria privada é criada em massa.

O endpoint legado de liberação aceita somente o payload sem destinos. Uma
tentativa de enviar `gallery_ids` é recusada sem mutação parcial. Para atribuir
fotos a uma cliente específica, use a etapa 05.

## Etapa 05 — Clientes e acesso

Os cards separam o estado da galeria do estado comercial e mostram disponíveis,
selecionadas e compradas. **Montar galeria privada** cria ou reutiliza somente a
privada da cliente escolhida e não marca as fotos como selecionadas ou
compradas. **Desvincular cliente** executa a operação assíncrona orientada pelo
backend; acompanhe o progresso e não repita a ação quando estiver bloqueada por
revisão financeira.

No resumo, cada pasta de conteúdo tem miniatura protegida e abre o mesmo
workspace da etapa 04 para revisar, adicionar ou excluir itens elegíveis. Pasta
técnica de capa não aparece nessa superfície.

## Painel Pagamentos

O painel agrupa pedidos e comunicações por cliente, inclusive quando a Galeria
pública operacional já foi removida. O resumo e as contagens obedecem aos
filtros combináveis de cliente, Galeria pública, período, situação financeira e
entrega da mensagem. Use **Limpar filtros** para retornar ao conjunto completo
e **Carregar mais** para avançar pelo cursor sem duplicar decisões.

Estados financeiros e de entrega são badges textuais independentes; cor nunca
é o único indicador. **Confirmar pagamento** e **Pagamento não localizado**
registram a primeira decisão imutável. **Tentar mensagem novamente** só aparece
quando o backend autoriza o retry. Falha de mensageria não altera a decisão
financeira, e a interface exibe somente erro sanitizado.

Detalhes de PIX manual e Evolution API permanecem em
[`OPERACAO-PIX-MANUAL.md`](OPERACAO-PIX-MANUAL.md) e
[`OPERACAO-NOTIFICACOES-PAGAMENTO.md`](OPERACAO-NOTIFICACOES-PAGAMENTO.md).

## Segurança, homologação e rollback

- use somente clientes, telefones, JPEGs e pedidos sintéticos em homologação;
- a interface serve prévias autenticadas e limitadas, nunca o original nem uma
  promessa de impedir screenshots;
- não registre PIX, telefone, corpo de mensagem, segredo ou credencial em logs,
  issues ou Git;
- as fontes são locais e não fazem requisição a Google Fonts ou outro terceiro;
- rollback de aplicação preserva a migration aditiva e o conteúdo publicado;
  durante rollback, desabilite upload em pasta publicada;
- downgrade de banco, limpeza de mídia e deploy exigem inventário e autorização
  humana específica.
