## Context

Ver `proposal.md` para motivação e escopo. Auditoria de planejamento realizada em 20/09/2026 sobre HEAD `235d2ff6e17fe666f63754df92f829c9d9fdb4f5`, preservando alterações locais preexistentes.

- `frontend/app/library/page.tsx` apresenta cards de carrinho separados dos cards das mesmas galerias. Links de carrinho apontam a `/library#cart`; a revisão real acontece em `/gallery/{id}?mode=review`.
- `frontend/app/client-shell.tsx` fornece a estrutura da biblioteca e galerias privadas. `frontend/app/public-galleries/[galleryId]/page.tsx` também tem cabeçalho próprio e precisa receber a mesma navegação após autenticação.
- `backend/app/client_commerce.py` projeta seleções persistidas, cotações, rascunhos e estado comercial por jornada. `PhotoSelection` já é a fonte da seleção por cliente/galeria; não é necessário criar um carrinho paralelo no navegador.
- `backend/app/checkout.py` sincroniza rascunhos e congela pedidos ao informar pagamento. O congelamento atual recalcula a seleção: o novo fluxo precisa comparar a revisão antes de congelar, sem trocar silenciosamente o conteúdo exibido.
- `SaleOrder` e `PaymentCommunication` atualmente representam um pedido por galeria e sua comunicação. As rotas em `backend/app/main.py` e os atalhos administrativos decidem um pedido por vez.
- O PIX global já fornece snapshots. Os pedidos antigos, as prévias protegidas, as exportações e as entregas devem continuar válidos.

### Compatibilidade entre mudanças

| Fonte existente | Decisão nesta mudança |
| --- | --- |
| `separate-client-cart-and-purchase-history`: `Agregação visual sem combinação financeira`, `Resumo global de carrinhos por jornada`, revisão separada e total apenas informativo | Substituídos pela revisão e pagamento únicos; não reimplementar essas restrições no apply ou ao sincronizar specs |
| `persist-client-cart-and-simplify-client-portal`: seleção no servidor e rascunho editável; exclusão de checkout global | Preservar persistência e congelamento na comunicação; substituir somente a exclusão do checkout global e os atalhos antigos |
| `add-manual-pix-checkout`: congelamento e remoção da seleção no checkout | Já evoluído por mudanças posteriores; seguir congelamento na comunicação, agora atômico para o conjunto |
| `centralize-client-and-pix-administration`: PIX global e snapshot por checkout | Preservar configuração protegida e snapshots; estender para o pagamento agrupado |
| `fix-purchase-previews-payment-shortcuts-and-expiry`: atalhos financeiros, prévias e prazos | Manter recursos; direcionar atalhos financeiros de integrantes ao conjunto e manter entrega por pedido |
| `configurable-push-and-whatsapp-notifications`: eventos e correções silenciosas | Um evento lógico por pagamento agrupado, preservando configurações de canal, outbox e silêncio em correções |

Essas mudanças anteriores não estão todas consolidadas em `openspec/specs`. Por isso os deltas desta mudança usam `MODIFIED` somente para requisitos presentes nas specs principais; requisitos novos ficam em `ADDED`. A reconciliação acima deverá acompanhar a revisão humana antes de sincronização/arquivamento, evitando restabelecer contratos supersedidos.

## Goals / Non-Goals

**Goals:**
- Uma composição revisada, um pagamento e uma decisão financeira, com pedidos operacionais rastreáveis.
- Transações e idempotência suficientes para concorrência real no PostgreSQL, preservando autorização e histórico.
- Migração aditiva e navegação compatível com URLs existentes durante a transição.

**Non-Goals:**
- Gateway, conciliação bancária automática, parcelamento, pagamento parcial, rateio manual ou nova política de reembolso.
- Recalcular faixas entre galerias, unir clientes, alterar consentimento push ou reorganizar produção e entrega.
- Combinar pagamentos históricos ou limpar rascunhos/dados por migration destrutiva.

## Decisions

### 1. Três destinos reais e revisão diretamente no carrinho

Usar `/library` para `Galerias`, `/library/cart` para `Carrinho` e `/library/purchases` para `Compras`, com detalhes vinculados ao histórico. O shell compartilhado oferece os três destinos e contador global; em mobile, usar navegação compacta persistente com espaçamento para a área segura. Galerias mantém somente seus cards de acesso. O botão flutuante leva à revisão global. Dentro da revisão não repetir um botão flutuante que navega para a própria tela.

Preservar retorno à galeria/pasta quando houver contexto disponível, sem tornar filtros ou posição de rolagem um novo requisito de persistência entre dispositivos. Após autenticação, revalidar dados e permissões no servidor. Adaptar links internos e tratar `/library#cart`, `/library#purchases` e `?mode=review` como entradas de compatibilidade para os novos destinos, sem redirecionar acessos a compras antigas para um carrinho vazio.

Alternativa descartada: manter três seções extensas na mesma página com âncoras. Isso conserva a duplicação e dificulta acesso consistente em galerias e dispositivos móveis.

### 2. Seleção existente como fonte; projeção global autorizada

Adicionar uma projeção de carrinho que reúna todas as jornadas autorizadas da identidade de sessão, com grupos visuais por galeria de origem e identificadores de seus pedidos/galerias privadas. Dentro dos grupos, informar pasta sem duplicar a foto por relações de referência. Reutilizar o escopo comercial vigente por pedido/galeria privada: agrupamento visual não recalcula descontos sobre quantidades de pedidos distintos. Cada foto selecionada participa uma vez conforme sua identidade comercial autorizada.

Retornar contagem global, subtotais, total pagável quando integralmente válido, elegibilidade e erros por grupo. Não mostrar soma parcial como valor para pagamento. Remoção de seleção expirada deve continuar possível sem conceder inclusão de novas fotos. Revalidar contador após mutações, mudança de conta e foco da janela; não apresentar cache anterior como autorização atual. Favoritos, seleção e histórico permanecem conceitos distintos.

Alternativa descartada: persistir um segundo carrinho em localStorage. Criaria divergência entre dispositivos e vazamento na troca de identidade.

### 3. Entidade de pagamento agrupado, mantendo SaleOrder

Introduzir entidade com UUID público, `client_id`, estado financeiro, revisão, total em centavos, snapshot PIX, datas UTC e vínculo aos pedidos. Um pedido pertence no máximo a um agrupamento ativo; somente pedidos da mesma cliente podem integrar o grupo. Reutilizar/estender comunicação e auditoria para que exista uma comunicação lógica do grupo, com referências aos pedidos, sem criar comunicações independentes concorrentes para cada integrante.

Os detalhes exatos dos nomes das tabelas/colunas serão fixados na implementação seguindo convenções existentes, mas as invariantes serão garantidas também por constraints e índices. Não mover `SaleOrderItem` para fora de seu pedido nem somar novamente o valor do grupo em relatórios que já agregam os integrantes.

Alternativa descartada: transformar todos os itens em um único SaleOrder de uma galeria arbitrária. Isso perderia origem, autorização, preços e operação de entrega por galeria. Uma associação apenas no frontend também não garante atomicidade.

### 4. Revisão versionada e transações completas

O GET do carrinho consulta a seleção e cotação sem criar pedidos. A entrada na tela prepara a revisão por uma mutação idempotente assim que a seleção válida estiver carregada, sem exigir um clique extra. Essa preparação cria ou reutiliza um único rascunho agrupado e snapshots dos pedidos, expondo revisão, total e PIX para conferência. Renderização repetida ou reenvio não pode proliferar rascunhos.

Bloquear a identidade comercial da cliente e depois as jornadas em ordem determinística. A mesma convenção deve ser usada por seleção, preparação, comunicação, decisões e rotas legadas que alterem pedidos integrantes. Ao comunicar, comparar a revisão apresentada com composição, cotação e elegibilidade atuais; divergência retorna conflito recuperável e exige nova conferência. Após validar tudo, congelar pedidos, gravar comunicação e eventos e consumir exatamente as seleções incluídas na mesma transação. Nunca fazer commits intermediários por galeria.

Uma comunicação já concluída com a mesma chave retorna o resultado original antes de revalidar prazos que possam ter expirado após a operação original, desde que a sessão ainda tenha acesso àquela compra. Reutilizar chave com outro conteúdo não executa uma segunda operação. Testar em PostgreSQL duas abas, repetição, comunicação simultânea com seleção e decisões administrativas concorrentes.

Alternativa descartada: chamar sequencialmente o endpoint atual de cada galeria. Uma falha intermediária deixaria a cliente com parte do PIX registrado.

### 5. Snapshots PIX e transição dos rascunhos antigos

Na primeira preparação agrupada, resolver a configuração global utilizável e congelar suas instruções. Atualizar seleção/cotação gera nova revisão explícita do rascunho, mantendo o snapshot PIX já iniciado; mudança global isolada não troca o recebedor de um pagamento em andamento. Um código sem valor fixo continua mostrando o total devido junto às instruções; um BR Code com valor fixo incompatível bloqueia a preparação, sem reescrever silenciosamente um código fornecido pelo fotógrafo.

Rascunhos legados continuam recuperáveis e seleções existentes aparecem no carrinho. Se houver checkout legado já preparado, sua associação ao grupo só é admitida quando os snapshots PIX são compatíveis; não substituir snapshot antigo nem escolher arbitrariamente entre recebedores. Em conflito, mostrar impedimento identificável e manter a recuperação do pagamento legado pelo seu detalhe, sem recombinar pagamentos já informados. Novas seleções e o caso usual com PIX global compatível seguem o fluxo único. Documentar essa exceção de migração no roteiro de homologação.

Compatibilidade compara código e instruções. Pedidos legados compatíveis conservam também os metadados de versão/configuração originais; o grupo guarda sua própria configuração. A remoção explícita de toda a seleção descarta rascunhos vazios e o grupo não comunicado, permitindo que um futuro carrinho independente use a configuração vigente.

Alternativa descartada: recalcular todos os snapshots com a configuração vigente em cada consulta. Poderia mostrar recebedor diferente depois de a cliente já ter transferido o valor.

### 6. Compras agrupadas, operações e notificações

`Compras` consulta projeção independente, incluindo grupos comunicados e pedidos legados sem grupo. Um grupo aparece uma vez com valor total, status financeiro, galerias, fotos e detalhes/entregas individuais. O estado de produção continua por pedido; não inventar uma entrega única para pedidos com entregas diferentes.

Confirmação, recusa e correção administrativas usam um serviço transacional comum. Rotas antigas para pedido integrante não podem alterar isoladamente seu estado financeiro: devem encaminhar para decisão explícita do conjunto ou retornar conflito com seu destino. Na UI, apresentar alcance e valor antes da decisão, conforme os controles administrativos já existentes. Correções registram auditoria e permanecem silenciosas. Eventos de pagamento usam o identificador do grupo para deduplicação; transporte continua assíncrono e falha de envio não desfaz pagamento registrado.

Alternativa descartada: permitir confirmar só um integrante do PIX. Criaria estados financeiros contraditórios sem existir um requisito de pagamento parcial.

## Risks / Trade-offs

- [Estado antigo em outra aba] → revisão comparada no servidor e atualização explícita antes da comunicação.
- [Concorrência entre endpoint antigo e novo] → serviço compartilhado, locks ordenados, constraints e testes reais PostgreSQL.
- [Uma seleção inválida impede o total] → apontar o grupo impedido, manter navegação e permitir remoção explícita; nunca excluir itens silenciosamente.
- [Pagamentos legados com PIX divergente] → preservar snapshots e tratamento de compatibilidade, sem combinação automática insegura.
- [Contagem/receita duplicada] → deduplicar histórico por grupo, conservar subtotais por pedido e testar relatórios/eventos existentes.
- [Navegação móvel cobre botões] → validar telas estreitas, zoom, leitor de tela, foco, diálogos e safe areas com a barra persistente.
- [Rollback para binário sem suporte ao grupo] → não habilitar escrita agrupada antes de existir caminho compatível de rollback; depois de dados agrupados, usar versão compatível ou correção adiante.

## Migration Plan

1. Implementar schema aditivo, constraints e leitura compatível. Ensaiar upgrade em banco isolado com pedidos e comunicações legados; nenhuma reclassificação financeira automática.
2. Implementar serviços agrupados e proteção dos endpoints antigos, projeções, administração e notificações antes de disponibilizar a interface que produz grupos.
3. Implementar navegação/revisão/histórico e adaptar URLs antigas. Validar fluxo completo com duas galerias, múltiplas pastas e uma compra legada, além de testes negativos de autorização e concorrência.
4. Registrar evidências locais, revisão do diff e roteiro de homologação. Antes de eventual deploy autorizado, apresentar inventário, portas/subdomínio, backup, versão de rollback compatível e plano restrito ao projeto `markina-gallery`.
5. Se somente CI estiver pendente, encerrar acompanhamento e aguardar o resultado enviado pelo usuário; não criar polling ou automação.
6. Homologar no navegador e mobile com o proprietário. Somente após revisão humana sincronizar specs e arquivar. Não reverter migration ou apagar grupos para rollback; preservar dados e operar com código compatível.
