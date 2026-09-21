## Context

Ver proposal.md. A limpeza pública preserva referências privadas e apaga arquivos antes de remover registros; a operação real falhou depois da etapa de storage. Pastas/fotos usam política comercial que cancela pendências e copia mídia comprada. Pedidos já possuem snapshots textuais e FKs anuláveis para fotos/galerias, mas seleções/interações dependem do acervo vivo.

## Goals / Non-Goals

Garantir exclusão completa com rastreabilidade, escopo seguro e recuperação idempotente. Não mudar política de desvinculação de clientes, enviar notificações de pagamento pela exclusão, excluir clientes nem iniciar limpeza retroativa por migration.

## Decisions

- Introduzir snapshots de movimentos removidos, com identidade do cliente, UUIDs históricos, nomes de galeria/pasta/foto, tipo e data do movimento. Não armazenar imagem nem segredo nessa tabela. Deduplicar pela identidade do registro original e tipo. Reutilizar snapshots de SaleOrder/Item para o financeiro, em vez de criar vendas fictícias para seleções sem pedido.
- Marcar pedidos afetados com `assets_removed_at`. Impedir sincronização/novo pagamento de rascunho indisponível sem alterar seu estado financeiro. Um grupo PIX ainda não comunicado afetado fica `unavailable` (estado de disponibilidade, não recusa); sua composição/total não mudam, e futuras seleções podem iniciar outro grupo. Grupos já comunicados mantêm decisões atômicas e acesso histórico.
- Separar preservação textual da antiga política de desvinculação. Exclusões de acervo preservam todos os estados e removem cópias históricas do escopo explicitamente excluído. Snapshots de pasta/foto usam contexto disponível; não inventar dados ausentes.
- Compartilhar preparação/remoção de registros entre galeria, pasta e foto; remover dependências em ordem, invalidar tarefas faciais e ajustes e revogar acesso. Galeria pública mantém somente tombstone técnico inativo para FKs e auditoria, sem pastas, fotos nem cartões visíveis. Privada removida apaga uploads próprios; referências públicas compartilhadas são apenas desvinculadas.
- Limpeza física confinada ao storage com registro durável de caminhos para retentativa; não silenciar falhas como sucesso. Retentativas priorizam jobs com menos tentativas para uma falha persistente não bloquear as demais limpezas. Operações antigas falhas exigem retentativa administrativa explícita, que atualiza manifesto e refaz a preparação idempotente para a nova política antes de continuar. Não executar retentativa automaticamente no deploy.
- Vendas e pagamentos exibe histórico textual de movimentos removidos com filtro de cliente/galeria/período. Cliente consulta somente seu histórico de pedidos e seleções removidas, sem URLs de arquivo inexistente. Preservar semântica dos estados: seleção não comprada não vira compra.

## Risks / Trade-offs

- [Remoção concorre com checkout] → locks de cliente e galeria e snapshot antes de apagar seleção; testes PostgreSQL.
- [Falha após remoção física] → nomes e estados já persistidos; retentativa idempotente conclui registros sem exigir arquivo.
- [Grupo com galerias diferentes] → conservar total/itens e estados de todos os integrantes; jamais confirmar parcialmente ou cobrar total recalculado silenciosamente.
- [Mídia compartilhada] → exclusão privada não remove original de outra galeria; exclusão da origem remove todo o acervo dependente conforme aprovação.

## Migration Plan

Migration aditiva 0059, sem varrer/excluir dados existentes. Downgrade deve recusar descarte de snapshots ou estado de indisponibilidade criado. Publicar por PR/CI; quando só houver CI pendente, parar. Homologação e retentativa da Galeria 01 seguem inventário e autorização operacional aplicável. Após exclusão real não há restauração de mídia pela reversão do código; corrigir adiante. Sincronizar/arquivar após aceite humano.

## Recuperação após recarregar a interface

A inspeção após o teste humano mostrou a operação antiga ainda com duas tentativas e updated_at de 20/09, sem nova execução. O proprietário confirmou ter clicado em Excluir Galeria 01 no diálogo. O resumo não retornava operação existente e a página guardava seu identificador somente em memória; ao reabrir, disparava outro DELETE, recusado por lifecycle_status=deleting. O resumo administrativo passa a retornar a última operação de delete_parent_gallery daquele alvo (não desvinculações). A página restaura acompanhamento, falha e ações; retentativa explícita exige inventário atualizado e usa POST na operação recuperada. Operação cancelada não bloqueia nova exclusão. GET e deploy nunca retomam limpeza automaticamente.
