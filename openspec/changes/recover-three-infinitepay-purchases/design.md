# Design

## Context

Base publicada 5446cf4d. PR #263 permanece independente, draft e CI verde no c41e274; não é necessário publicá-lo para recuperar este lote. A decisão mais recente do proprietário dispensa confirmação externa para eae11005, e2194ce5 e 11f18369. O código publicado aceita exception e cancelled, impede confirmação automática de exception e só expõe URL de awaiting_payment. A reserva de fotos considera pedidos confirmados ou pending/frozen, portanto pedidos cancelled deixam de bloqueá-las.

## Goals / Non-Goals

**Goals:** recuperar as 22+1+1 fotos elegíveis no tenant 1531dbaa-215c-4583-b1f0-77d185ad7f07; validar novo PIX local; auditar sem alterar a verdade do provedor.

**Non-Goals:** cancelar na InfinitePay, confirmar recebimento, resolver HTTP 422, ativar configuração, adicionar botão público de bypass, migration, deploy, interferir no cofre/PR #262 ou manutenção/PR #261.

## Decisions

Ferramenta isolada em backend/operations, sem imports ou rotas no produto. Allowlist fixa de três pagamentos e valores: eae11005-d1f2-46f4-861e-90a3ff3a923d=15400; e2194ce5-8fd2-47bc-a6da-53d182b3687a=5; 11f18369-3b0a-4337-8549-685e5b2ce195=5. Estado inicial esperado awaiting_payment para o primeiro, verification_required para os demais. Estados, revisões, tentativas, recibos, pedidos, snapshots, seleções e configuração integram pré-imagem/fingerprint. Exigir ator administrativo da conta ativa.

Travar conta com FOR NO KEY UPDATE, clientes ordenados e pagamentos/pedidos ordenados na transação. O teste PostgreSQL reproduziu deadlock quando o lock da conta era FOR UPDATE: um confirmador já segurava Client e inseria recibo cuja FK pede KEY SHARE em Tenant. NO KEY UPDATE serializa preparações existentes e permite essa FK concluir antes da recuperação obter Client. Não alterar o helper global do produto nesta operação. Recusar alvos com confirmação, NSU, recibo verificado, pedido não pendente/congelado, entrega ou divergência de soma de snapshots. Validar todos antes de alterar qualquer um. Alterar somente estado/revisão/update da compra para exception e payment_status local dos pedidos para cancelled; manter frozen_at e toda associação/snapshot. Restaurar PhotoSelection conforme parent/derived do pedido, somente se ausente. Não reutilizar _restore_local_selection: ela desfaz a ligação com o cartão e não preserva a mesma associação histórica.

Preparar PIX com prepare_group e conferir cart_payload: fotos restauradas visíveis, can_prepare/pix_available verdadeiros, sem card_payment bloqueante. Isso também detecta prazo, acesso, outro pedido congelado e configuração PIX incompatível. O rascunho é local; não há HTTP, comunicação de pagamento ou mensagem externa. O novo total segue regras atuais, sem alterar os valores congelados anteriores. A simulação informa quantitativos/totais novos para revisão.

Auditoria append-only por pagamento com referência fixa da operação, ator, estado/revisão anterior e grupo PIX novo, respeitando 320 caracteres. Reexecução auditada retorna sem mutação, inclusive se a seleção já tiver sido consumida por outro pagamento. Lote parcialmente auditado é recusado. CLI exige fingerprint da simulação e reconhecimento de que o link remoto pode continuar pagável para aplicar. Registrar pré-imagem sem dados pessoais, credenciais ou URLs em arquivo 0600 no servidor antes da aplicação.

Simulação usa a mesma transação e rollback obrigatório; falha também reverte tudo. Nenhum commit ocorre em helpers. Aplicação é uma única transação. O processo operacional não modifica imagem, serviço, configuração, schema ou arquivos do app instalado; executa a ferramenta validada no ambiente API existente.

## Risks / Trade-offs

- [Link remoto ainda pagável] → risco residual explicitamente comunicado; remover retomada local não invalida uma URL já copiada. Não oferecer garantia de ausência de cobrança dupla. Evidência tardia continua em exception/recibo/auditoria para conciliação humana.
- [PIX pode ser pago após commit] → rollback financeiro automático após disponibilização é impróprio; reverter somente falhas antes do commit. Pré-imagem serve para auditoria/conciliação, não autorização de restauração cega de banco.
- [Seleção/pagamento muda] → locks e fingerprint recusam execução obsoleta; nenhuma alteração na compra confirmada 04381887.
- [Texto antigo em Compras] → histórico antigo ficará em análise/exceção; a escolha disponível é retomada no Carrinho. Não prometer botão novo em Compras sem publicação de UI.

## Migration Plan

Sem migration ou deploy. Validar ferramenta em dados sintéticos/PostgreSQL; executar CI pertinente; inventariar API, versão, tenant e recursos próprios; simular lote com rollback e salvar pré-imagem protegida; revisar resultado e aplicar somente o lote autorizado; reconsultar escolhas/total e registros antigos por leitura. Interromper diante de qualquer premissa divergente. Nenhuma restauração global ou exclusão de dados de terceiros.
