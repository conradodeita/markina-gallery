# Context

Fontes oficiais conferidas: https://ajuda.infinitepay.io/pt-BR/articles/10766888-como-usar-o-checkout-integrado-da-infinitepay documenta X-Api-Key, options.payment_methods_enabled=[credit_card,pix], single_payment e webhook.events paid; https://www.infinitepay.io/checkout-documentacao mostra capture_method pix no payment_check e retorno; https://www.infinitepay.io/checkout anuncia PIX taxa zero. O adaptador atual envia somente cartão; parser entende PIX, domínio rejeita. O retorno atual depende de a cliente voltar ao site.

# Goals / Non-Goals

Implementar checkout misto seguro e Carrinho coerente, mantendo PIX manual, isolation, snapshots, idempotência, conciliação e pagamento confirmado. Não interpretar webhook sem consulta como prova, implementar estornos automáticos, encerrar links remotos sem contrato ou habilitar PIX em produção nesta missão. Sem descontos/parcelamento novos, atualização de endpoints/auth ou segredo.

# Decisions

1. Migration0086 aditiva em ProviderPayment: checkout_methods_snapshot com default legado credit_card, capture_method verificado nullable, cart_dismissed_at nullable. Novas emissões fixam credit_card+pix. Links existentes não são reemitidos nem prometem PIX; guard de confirmação aceita somente método do snapshot. Receipt/digest inclui método; confirmação grava método com NSU atomicamente. Downgrade recusa se estado novo estiver em uso; rollback operacional exige API compatível.
2. Capacidade tipada permite lista explícita de meios; não remover validação de contrato em issue_provider_payment. Payload usa snapshot da compra para criação. Mantém single_payment, chaves de tenant/compra, perfil e limites existentes. Mínimo local100 aplica ao checkout InfinitePay misto; PIX manual independente.
3. Webhook usa objeto webhook.url/events=[paid] oficialmente documentado. Rota pública limitada por tamanho, schema e rate limit recebe order_nsu/transaction_nsu/invoice_slug; ignora valores/método alegados para confirmação e consulta payment_check com credencial histórica. Sem assinatura documentada não alegar autenticação. Não aceitar URL do caller nem registrar corpo/segredos. Resposta200 só após processamento seguro; falha transitória400 permite retry documentado. Idempotência e locks do domínio preservam uma confirmação.
4. Carrinho projeta pendências externas separadas da seleção nova, com snapshots das fotos, valor congelado e mesma URL validada. Compras omite awaiting_payment/creating/verification_required sem evidência financeira pendente. Exceções e evidência tardia permanecem conferíveis. Pendência não permite PIX manual/segunda emissão das mesmas fotos. Rótulo:Continuar pagamento na InfinitePay; explicação cartão ou PIX no mesmo checkout, condicionada aos meios do snapshot. Links antigos:continuar cartão sem prometer PIX.
5. Esvaziar checkout externo é desistência visual da intenção, não recuperação financeira. DELETE por UUID/owner ativo, locks Client→ProviderPayment e revisão esperada; marca dismissed_at e auditoria. Não cancela pedido, muda estado financeiro, apaga itens ou libera reserva. GET não desfaz desistência. Retorno posterior confirma quando válido ou mantém conferência; nunca restaura seleção automaticamente. A cliente pode esvaziar seleções novas pelo fluxo atual sem efeitos sobre outras pendências. Explicar que o link anterior não é cancelado automaticamente.
6. Projeções mostram método confirmado real (PIX InfinitePay ou cartão), distinguindo PIX manual. Não habilitar ações manuais PIX em ProviderPayment. Campo/API legado card_enabled continua chave de ativação da integração por compatibilidade, com textos claros dos dois meios. APIKey/OTP/cofre inalterados.

# Risks / Trade-offs

Esconder intenção não garante link expirado; snapshots continuam reservando fotos e retorno tardio conciliável. Mudança de schema altera plano de release de0085 para0086, exige inventário/backup/restore e API compatível antes de web. Webhook síncrono pode exceder preferência de1s por depender de consulta; timeout/retry seguros, sem falsa promessa de latência. Nenhuma API de cancelamento comprovada. Mudança de configuração geral não modifica links antigos.

# Migration Plan

O contador do webhook é persistido antes da consulta externa; rollback de falha transitória não apaga a tentativa. A consulta continua repetível sob o limite, sem reemitir checkout ou aplicar confirmação pelo payload.

Local/testes sintéticos somente. Migration0086 preserva legado com crédito exclusivo e método desconhecido em confirmações antigas, sem inventar método. Futuro release coordenado após cadeia0085→0086, backups/keyring/restore, revisão e autorização. Manifesto0084 continua recusando a branch; não ampliá-lo. Após adoção mista não retornar API que rejeita PIX; manter imagens compatíveis e receipts.

# Validation

## Preparação operacional — 22/10/2026

Na troca coordenada, a barreira temporária SHALL impedir novas escritas e preservar saúde/retorno. Antes da API0086 saudável, o novo webhook recebe400 explícito para retentativa, sem alegar processamento. Após migration aditiva, uma instância temporária da mesma API0086, apenas na rede interna e com configuração segura somente de API, SHALL manter retorno/webhook enquanto a instância principal é substituída. Só após saúde da principal o upstream volta a api e a barreira é removida. Renderizador aceita somente api ou payments0086-api-canary; não altera workflow0084 ou proxy de terceiros. Ensaiar desligamento/substituição real da API sintética com callbacks pela temporária antes de propor execução remota.

Geração inicial do keyring SHALL ser manual, com senha de backup em terminal interativo, sem argumentos/segredos no chat. O preparador faz escrita exclusiva de arquivo0600 fora do checkout e backup AES-GCM independente, derivado com scrypt(n=131072,r=8,p=1), verificado antes do material ativo. Chave mestra aleatória de32bytes; não é a APIKey do fotógrafo. Ausência de keyring é pré-condição; material existente nunca é sobrescrito. Host/owner/modo do diretório, ambiente staging, marcadores de operação e confirmação da senha são validados. Falha parcial preserva arquivos para reconciliação. Somente API candidata carrega o material; demais serviços e binding legado permanecem intocados. O proprietário guarda somente arquivo cifrado no PC e senha separada. Provisionar não é publicar, nem comprova custódia externa ou restauração do backup real. O helper antigo de manutenção bloqueia o novo webhook e não pode ser reutilizado como prova de continuidade neste release sem ajuste/revisão/ensaio próprios.

Regressões de payload misto/legado, captura PIX e cartão, mismatch/snapshot, retorno e webhook falsificado/duplicado/tardio, concorrência, downgrade protegido e isolamento. Carrinho com fotos/retomada/remoção/refresh, Compras PIX informado/recusado/confirmado e entregas; PIX manual intacto, limites100, idempotência e nenhum segredo. Gates locais e CI final do mesmo PR.
