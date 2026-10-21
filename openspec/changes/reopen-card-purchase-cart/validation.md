# Continuidade e evidências — 21/10/2026

## Decisão e isolamento

O proprietário aprovou recuperação manual por compra sem retorno/falha inconclusiva, com as fotos já escolhidas prontas no carrinho para cartão/PIX. Confirmados e falhas claras não usam essa exceção. Proposal/design/delta e tasks criados antes do código e validados em modo estrito, incluindo a reconciliação explícita do delta ativo add-infinitepay-credit-payments.

Worktree própria C:/codex-data/worktrees/reopen-infinitepay-cart/Photo Delivery, branch feature/reopen-infinitepay-cart, base c41e274 do PR #263. Nenhuma branch de #261/#262/#263/#264 foi modificada. A recuperação real anterior está documentada no PR #264, com escopo independente; esta implementação não modifica banco remoto, chave, configuração, serviço ou pagamento real.

## Task 1.1

Serviço app/provider_cart_recovery.py implementado: prévia sob savepoint revertido, confirmação sem commit interno, tenant/admin/client/snapshots/recibos validados, fingerprint do contexto e cotação efetiva, recuperação por par galeria+foto, preservação de seleções novas, preço atual e idempotência auditada. Retém associação e preço antigo e não usa a decisão PIX para marcar cartão recebido. Métodos permanecem os configurados; cartão sem PIX é permitido.

- SQLite inicial: **17 aprovados, 23 avisos, 511,53 s**. Antes de terminar foram acrescentados três cenários adicionais ao arquivo; esses não fizeram parte dessa coleta inicial.
- Matriz PostgreSQL após os acréscimos: **20 aprovados, 6 avisos, 125,07 s**. Inclui restauração exata dos pares galeria/foto, prévia sem efeito, fotos novas preservadas, PIX/card isoladamente, fundos confirmados/NSU/recibo, falha clara, prazo, snapshot, contexto obsoleto, motivo/aceite, rollback do chamador, repetição após nova compra, administrador A/B e preço atual sem reescrever o antigo.
- Ruff do serviço e testes aprovado. Testes usam apenas provedor/conta sintéticos. Nenhum checkout ou pagamento externo foi criado.

PostgreSQL local exclusivo do ensaio: container pyp-cart-recovery-test, label codex.task=reopen-card-purchase-cart, ID 93c8a61d96e8da661de23c89ac3d915690774ae3afae649bf632188f09e15caa, porta 127.0.0.1:15470, banco pyp_photographer_test, dados em tmpfs. Recursos preexistentes foram verificados e não foram alterados. Parar somente esse container após concluir os ensaios.

Revisão proporcional: usa cart_payload/cotação/autorizações existentes. _restore_local_selection não serve porque remove associações históricas. O script isolado/allowlist do PR #264 não é dependência do runtime. Não houve oportunidade necessária de excluir código funcional ou fazer refatoração geral.

## Pendências acionáveis

Task 1.2: reproduzir/proteger resposta de emissão que chega após reabertura e executar corridas PostgreSQL. API/projeção e UI ainda não implementadas (2.1/2.2). Gates amplos/PR ainda pendentes (3.1). A instalação npm ci --ignore-scripts concluiu com lockfile existente; não houve atualização de dependências. O guia Next instalado use-client foi lido antes da futura UI.

Nada desta change foi publicado. Validação visual autenticada de cliente e homologação de novos retornos reais não foram executadas; não declarar essas etapas como testes locais aprovados.
