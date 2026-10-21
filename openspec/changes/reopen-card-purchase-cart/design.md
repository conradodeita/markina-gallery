# Design

## Context

Ver proposal.md. O proprietário esclareceu em 21/10/2026: o cliente precisa do carrinho pronto novamente com as fotos escolhidas para tentar cartão ou PIX; a decisão manual ocorre no card da cliente. Delimitou: pagamentos PIX/cartão confirmados não são reabertos; negativas claras seguem a documentação; a ação atende falta de retorno/falha inconclusiva. Depois confirmou: “Eu acho que é esse o caminho”. Esse é o aceite funcional do comportamento delimitado. Não se trata de confiar em um evento externo, marcar recebido ou afirmar cancelamento do provedor.

A recuperação pontual do PR #264 foi aplicada e verificada na versão publicada 5446cf4d; o script permitia somente três UUIDs. Esta change não amplia aquele script nem repete a operação real. O PR #263/c41e274 filtra pendências pelas fotos do carrinho e é a base desta implementação, para preservar compras independentes. As mudanças de cofre/Python continuam fora do escopo.

O delta ativo de add-infinitepay-credit-payments proibia qualquer liberação local de cobrança ainda pagável. Reconciliar esse texto somente com a exceção manual ora aprovada, preservando a proibição de liberação automática e de ação pela cliente. Não modificar a branch do PR #263; sua correção de projeção continua sem poder recuperar reservas por conta própria.

## Goals / Non-Goals

**Goals:** ação manual reutilizável e explícita no painel; recuperar seleção integral para escolha dos meios existentes; preservar propriedade, histórico, concorrência e idempotência.

**Non-Goals:** reabrir automaticamente por prazo ou HTTP, confirmar dinheiro manualmente como cartão, cancelar no provedor, implementar webhook/monitor universal, habilitar cartão/PIX, publicar ou alterar dados reais nesta change.

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

## Risks / Trade-offs

- [Link antigo pode continuar pagável] → decisão manual explícita e auditada, sem garantia de cancelamento remoto; preservação de exceção/evidência e bloqueio de confirmação automática do pedido cancelado.
- [Cliente ou configuração muda entre prévia e ação] → fingerprint e locks; solicitar nova prévia e reverter integralmente.
- [Retorno tardio de criação] → guarda de transição testada; nunca regredir estado final ou reaberto.
- [Nova compra já consumiu as fotos] → idempotência pela decisão registrada, sem executar restauração novamente.

## Migration Plan

Sem migration. Testar localmente com dados sintéticos e PostgreSQL isolado. Preparar PR draft empilhado sobre #263, sem alterar sua branch nem #261/#262/#264. Publicação futura de API e web coordenada, mediante autorização, inventário e gates existentes; preservar worker/infraestrutura. Rollback de código deve continuar compreendendo exception/cancelled, que já existem na versão publicada; não desfazer recuperações ou restaurar banco automaticamente após nova atividade da cliente. Sincronização/arquivo somente após revisão humana.
