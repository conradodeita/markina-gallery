# Context

O pagamento reaberto fica exception, pedidos cancelled e evento de auditoria preservado. As fotos voltam à seleção editável. Atualmente Compras renderiza essa tentativa como compra e o painel principal mantém o card. A tentativa técnica deve ter projeção separada.

# Goals / Non-Goals

Separar tentativa encerrada do pedido ativo, sem apagar rastreabilidade ou esconder evidência tardia. Não cancelar link remoto, emitir novo pagamento, reabrir confirmado, mudar eligibility, migração, keyring ou inventários. A remoção de fotos altera somente seleção, não equivale a cancelamento na InfinitePay.

# Decisions

1. Reutilizar cart_recovery_statuses como classificação derivada e isolada por tenant. Acrescentar requires_reconciliation: recuperação auditada com receipt queued/processing/verified ou recebido após a recuperação (inclusive ignored/failed), NSU, confirmed_at ou estado diferente de exception. Informação tardia sem confirmação de pagamento é conferência, não receita. Comparar o instante de processamento ou criação do receipt à recuperação para reconhecer também reprocessamento posterior de receipt antigo.
2. Cliente: omitir somente exception com recuperação auditada sem reconciliação necessária da projeção Compras. Manter o carrinho como único acesso à seleção. No frontend, ausência do marcador de conferência em resposta antiga conserva a ocorrência visível; somente false explícito autoriza a defesa de ocultação local. A API nova já omite a tentativa histórica. Ocorrência com evidência tardia volta à lista com rótulo de conferência, sem URL antiga ou ação de pagamento. Pagamento confirmado continua visível. Sem apagar registros, sem filtrar exceções não reabertas.
3. Fotógrafo: lista e totais principais excluem somente essas tentativas. Filtro explícito financial_status=reopened consulta o histórico da própria conta, rotulado Tentativa encerrada por reabertura, sem ação financeira/entrega. Evidência tardia aparece na lista principal como Conferência após reabertura. Filtros, paginação e exportação usam a mesma projeção.
4. Manter os paths API/proxy existentes; filtro opcional validado explicitamente. Estado financeiro armazenado continua inalterado. Não condicionar visibilidade ao carrinho vazio: reabrir já encerra a participação daquela tentativa na compra ativa.

# Risks / Trade-offs

- Falha de auditoria: sem evento válido não ocultar tentativa.
- Retorno tardio: não confundir ausência no painel com ausência de cobrança; manter guards financeiros e conferir evidência nova.
- Cliente limpa seleção: não restaurar automaticamente fotos nem apagar/reabrir histórico.
- Snapshot0084 continua sem cofre e sem este runtime novo; a branch integrada permanece protected/recusada para publicação por esse fluxo.

# Migration Plan

Sem schema ou atualização de registros. Publicação futura coordenada API/web no plano0085 da branch integrada, após CI/revisão/autorização. Rollback compatível pode restaurar projeção anterior sem desfazer recuperações, fotos removidas ou registros financeiros.

# Validation

Reutilizar testes HTTP sintéticos de recuperação/seleção/PIX, acrescentar cenário remover todas as fotos, nova compra, isolamento, comprovantes tardios e falhas sem evento. Regressões frontend cliente/painel/filtro/rotulagem; executar suites pertinentes, lint/build/TypeScript/Ruff/OpenSpec/política, CI final do PR integrado.
