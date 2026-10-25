# Design

## Context

Ver proposal.md. O proprietário esclareceu em 21/10/2026: o cliente precisa do carrinho pronto novamente com as fotos escolhidas para tentar cartão ou PIX; a decisão manual ocorre no card da cliente. Delimitou: pagamentos PIX/cartão confirmados não são reabertos; negativas claras seguem a documentação; a ação atende falta de retorno/falha inconclusiva. Depois confirmou: “Eu acho que é esse o caminho”. Esse é o aceite funcional do comportamento delimitado. Não se trata de confiar em um evento externo, marcar recebido ou afirmar cancelamento do provedor.

A recuperação pontual do PR #264 foi aplicada e verificada na versão publicada 5446cf4d; o script permitia somente três UUIDs. Esta change não amplia aquele script nem repete a operação real. O PR #263/c41e274 filtra pendências pelas fotos do carrinho e é a base desta implementação, para preservar compras independentes. As mudanças de cofre/Python continuam fora do escopo.

O delta ativo de add-infinitepay-credit-payments proibia qualquer liberação local de cobrança ainda pagável. Reconciliar esse texto somente com a exceção manual ora aprovada, preservando a proibição de liberação automática e de ação pela cliente. Não modificar a branch do PR #263; sua correção de projeção continua sem poder recuperar reservas por conta própria.

## Goals / Non-Goals

**Goals:** ação manual reutilizável e explícita no painel; recuperar seleção integral para escolha dos meios existentes; preservar propriedade, histórico, concorrência e idempotência.

**Non-Goals:** reabrir automaticamente por prazo ou HTTP, confirmar dinheiro manualmente como cartão, cancelar no provedor, implementar webhook/monitor universal, habilitar cartão/PIX ou alterar dados reais nesta change. A publicação exige a etapa operacional explicitamente autorizada abaixo.

## Decisions

### Serviço e prévia

Implementar serviço próprio de recuperação por UUID de ProviderPayment. Contexto deriva da sessão administrativa ativa. Usar os modelos atuais e AuditEvent, sem migration. POST de prévia executa as mesmas guardas/restauração/validação sob transação revertida, produzindo apenas dados mínimos e fingerprint; não cria checkout ou grupo PIX. POST de confirmação exige fingerprint, revisão, UUID de idempotência, motivo de até 100 caracteres e aceite do risco remoto. O valor e as fotos da prévia são revisáveis antes da decisão.

Travar Tenant FOR NO KEY UPDATE, Client e compras/pedidos/itens em ordem estável; o modo da conta preserva compatibilidade com a FK do recibo do confirmador. Gerar fingerprint de estados, recibos, snapshots, seleção e contexto de cotação/configuração. Recusar outras contas, estado fora de awaiting_payment/verification_required, fundos confirmados, recibos queued/processing/verified, entrega, itens ou totais divergentes. Validar novamente antes de qualquer commit.

### Efeitos locais e repetição

Conservar associação dos pedidos ao ProviderPayment, frozen_at, itens, preços e URLs. Alterar a compra antiga para exception e pedidos para cancelled. Restaurar PhotoSelection ausentes conforme parent/derived e validar cart_payload: todas as fotos antigas visíveis e can_prepare=true. O carrinho usa preços atuais e não exige PIX se cartão estiver disponível. Não chamar _restore_local_selection porque desfaz associações históricas. Não preparar PIX antecipadamente: a cliente escolhe pelo fluxo normal.

AuditEvent registra em subject limitado a 320 caracteres compra, UUID idempotente, ator, estado/revisão anterior e motivo limitado. Consultar auditoria sob locks antes de restaurar; a mesma decisão retorna resultado anterior sem modificar nova seleção/compra. Chave diferente para compra já reaberta é conflito, nunca restauração repetida. As transações da API são os únicos commits; prévia usa savepoint revertido e erros revertem a operação inteira.

### Resposta externa concorrente

issue_provider_payment grava incerteza antes da rede, mas atualmente pode sobrescrever exception com awaiting_payment quando a URL chega. Após a rede, reler com lock e conservar estados finais/reabertos; reter diagnóstico/URL da resposta antiga sem expô-la como retomável. Não mudar endpoint, autenticação, retry externo ou contrato do provedor.

### UI e compatibilidade

Acrescentar capacidade/revisão e indicador de reabertura à projeção administrativa, reconhecendo também a auditoria da recuperação operacional anterior sem repetir seus efeitos. No card da cliente, ação por compra identificada, sem confirmação PIX e sem alterar um status global. Prévia informa quantidade, total atual, meios disponíveis e reconhecimento simples de que o link anterior não é encerrado automaticamente. Só o envio final confirma; duplo clique, rede incerta e conflito de sessão preservam a decisão e atualizam o painel. Após sucesso: Carrinho reaberto; a cliente pode escolher novamente como pagar. Manter filtros, fotos, paginação e entregas.

A leitura do carrinho inclui uma revisão opaca da última recuperação autorizada daquele cliente/tenant. O refresh por foco já existe; ao receber nova recuperação com carrinho elegível e sem emissão bloqueante, a UI descarta a chave antiga e conserva as fotos devolvidas pelo servidor. Chaves de cartão também pertencem à revisão da seleção: falha incerta na mesma revisão mantém a chave, enquanto seleção diferente usa chave nova. Nunca emitir automaticamente ou usar simples ausência de URL/tempo como sinal de reabertura. Resposta terminal atrasada força nova leitura, sem manter bloqueio local obsoleto. O backend continua recusando nova cobrança de fotos reservadas, independentemente da chave enviada.

### Histórico e rascunho PIX após recuperação

O proprietário apontou aparência de duplicação em c648edb4/e1d93b85 durante a implementação. Consulta Oracle estritamente read-only confirmou: o primeiro pedido está cancelled, vinculado à compra eae11005 em exception e à auditoria operacional; o segundo contém as mesmas 22 fotos/R$154, mas é pending/unfrozen/unconfirmed, sem ProviderPayment e ligado a PaymentGroup draft. Nenhuma mutação foi executada. A preparação normal do PIX pelo carrinho cria esse rascunho interno; sua existência técnica não equivale a compra informada.

Reutilizar a auditoria de recuperação na projeção da própria cliente: histórico antigo indica Carrinho reaberto e permite Abrir carrinho, sem URL antiga nem mensagem genérica de reserva/conferência. Na projeção financeira administrativa, omitir somente pedido pending, não congelado/confirmado/removido, vinculado a grupo PIX draft e sem comunicação por grupo/pedido nem provedor. As fotos permanecem em Seleções em aberto; report_group continua promovendo a compra pelo contrato existente. Não excluir registros/banco, esconder confirmação real nem modificar preços/snapshots. Esse tratamento aplica o requisito já existente de unified-client-cart-and-pix: preparar QR Code mantém carrinho, sem nova compra no histórico.

O proprietário esclareceu depois que o fotógrafo também não deve visualizar pedidos iguais em outras telas. Centralizar a condição somente de projeção em order_visibility e reutilizar no painel, pedidos da galeria legada e contador comercial do diretório. Manter contagem bruta separada para deletion_eligible e inventários; nenhuma regra de exclusão ou proteção comercial é flexibilizada. A projeção comercial por cliente/galeria e o histórico de compras já excluem rascunhos; verificar esses consumidores por regressão, sem refatoração geral. A lista de pedidos da galeria identifica recuperação auditada com o mesmo rótulo, preservando os snapshots originais.

## Risks / Trade-offs

- [Link antigo pode continuar pagável] → decisão manual explícita e auditada, sem garantia de cancelamento remoto; preservação de exceção/evidência e bloqueio de confirmação automática do pedido cancelado.
- [Cliente ou configuração muda entre prévia e ação] → fingerprint e locks; solicitar nova prévia e reverter integralmente.
- [Retorno tardio de criação] → guarda de transição testada; nunca regredir estado final ou reaberto.
- [Nova compra já consumiu as fotos] → idempotência pela decisão registrada, sem executar restauração novamente.

## Migration Plan

Sem migration. Testar localmente com dados sintéticos e PostgreSQL isolado; estender somente o passo de checkout PostgreSQL do CI para incluir os testes de recuperação, pois SQLite não comprova locks/concorrência. Preparar PR draft empilhado sobre #263, sem alterar sua branch nem #261/#262/#264. Publicação futura de API e web coordenada, mediante autorização, inventário e gates existentes; preservar worker/infraestrutura. Rollback de código deve continuar compreendendo exception/cancelled, que já existem na versão publicada; não desfazer recuperações ou restaurar banco automaticamente após nova atividade da cliente. Sincronização/arquivo somente após revisão humana.

### Autorização e preparação operacional de 21/10/2026

Após CI completo aprovado no head 6f4a903, o proprietário autorizou o deploy. O preflight read-only confirmou o checkout 5446cf4d, schema 20261017_0084, API/web saudáveis e HTTPS válido. O verificador local recusou a publicação com api_fora_do_escopo: sua allowlist e o manifesto ainda descrevem runtimes anteriores. Corrigir somente a preparação do gate, sem mudar a implementação já testada.

Acrescentar à allowlist e fixar no manifesto os dez runtimes necessários: backend/app/client_lifecycle.py, backend/app/order_visibility.py, backend/app/provider_cart_recovery.py, backend/app/unified_checkout.py; frontend/app/admin/galleries/[galleryId]/orders/page.tsx; frontend/app/admin/payments/cart-recovery.tsx e cart-recovery.module.css; frontend/app/library/cart/page.tsx, purchase-card.tsx e purchases/page.tsx. Atualizar os hashes dos runtimes já permitidos alterados pelo mesmo candidato. Permitir somente os cinco testes frontend correspondentes como operações sem runtime; não adotar prefixos genéricos. Avançar a baseline para o SHA saudável observado 5446cf4d7328ef6283ebfab50b5d1976d561fc8d, preservando schema, pins de dependências existentes e contratos de manutenção/rollback.

Testar recusa de blob divergente e aprovação só depois da atualização exata, preservando as regressões de worker, Monitor, cofre, migration e dependência fora do escopo. O helper emergencial existente deriva a API da imagem ativa e compara todas as distribuições; os quatro pins já aprovados não autorizam versões novas nem atualização de outros consumidores. Nenhum script de release, wrapper SSH, Docker/Compose ou configuração secreta será alterado por essa preparação. O novo head precisa de CI próprio antes da integração/publicação.

### Decisão posterior de apresentação — hide-reopened-purchase-from-active-lists

O proprietário aprovou retirar a tentativa auditada reaberta de Compras e das pendências principais, mantendo histórico administrativo explícito e ocorrências com evidência tardia para conferência. A nova change substitui somente a apresentação anterior de Carrinho reaberto/Abrir carrinho no histórico da cliente. Preservação financeira, restauração inicial das fotos, decisões auditadas, idempotência, seleção editável e guards tardios desta change continuam vigentes. O release anterior permanece evidência histórica; este comportamento novo ainda exige seu próprio CI e publicação autorizada.
