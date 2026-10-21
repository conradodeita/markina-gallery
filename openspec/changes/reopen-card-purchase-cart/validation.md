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

API/projeção e UI implementadas e validadas em 2.1/2.2. Gates amplos/PR ainda pendentes (3.1). A instalação npm ci --ignore-scripts concluiu com lockfile existente; não houve atualização de dependências. O guia Next instalado use-client foi lido antes da UI.

Nada desta change foi publicado. Validação visual autenticada de cliente e homologação de novos retornos reais não foram executadas; não declarar essas etapas como testes locais aprovados.

## Task 1.2

Regressão reproduzida antes da correção, em PostgreSQL: a resposta accepted após uma reabertura fazia a compra voltar de exception para awaiting_payment (**1 falha, 27 desmarcados, 10,95 s**). A resposta antiga poderia prender novamente as fotos que já haviam voltado ao carrinho. issue_provider_payment agora relê sob locks da conta NO KEY UPDATE, cliente, compra/tentativa; atualiza o diagnóstico, mas preserva estados concluídos/reabertos, URLs históricas e associações. Recusa clara tardia não desfaz o histórico de uma recuperação já concluída.

O primeiro ensaio após essa guarda passou accepted/refused/unknown, mas detectou retorno ORM desatualizado na falha de transporte (**3 aprovados, 1 falha**): o banco continuava em exception, porém o chamador recebia verification_required. O catch agora atualiza a leitura antes de retornar, sem nova emissão.

Matriz final dirigida de concorrência: **10 aprovados, 20 desmarcados, 6 avisos, 77,37 s** em PostgreSQL. Abrange quatro respostas tardias (accepted/refused/unknown/transport), duas sessões reabrindo uma vez, três corridas com confirmação, confirmação concluída antes da URL e evidência tardia sem alterar o PIX novo. Ruff aprovado. Nenhuma alteração de endpoint, payload/autenticação, prazo, segredo ou contrato de reemissão do provedor.

O CI do PR operacional #264 terminou success também no head documental final f4717c3, run 39643689877. Seu corpo foi atualizado com o resultado, sem novo commit, merge ou deploy. Esse CI não valida esta nova change; os gates próprios de 3.1 permanecem pendentes.

## Task 2.1

POSTs administrativos de prévia/confirmação exigem sessão administrativa, tenant derivado do servidor e mesma origem; inputs extras são recusados. A projeção inclui capacidade/revisão/indicador sem expor motivo ou dados secretos. Reconhece a auditoria operacional anterior do #264. GET do próprio carrinho inclui UUID opaco da última recuperação da própria cliente/conta, sem permitir reabertura pela cliente.

PostgreSQL: **12 aprovados, 6 avisos, 89,57 s** em tests/test_provider_cart_recovery_api.py. Cobertura: autenticação real, cliente/visitante recusados, tenant B sem acesso a A, motivo/aceite/fingerprint/revisão/origem/tenant no body, repetição HTTP, projeção e revisão privada, cartão confirmado e PIX confirmado preservados; mistura de fotos canônicas e legadas restaura os quatro pares originais sem criar galeria adicional. Ruff aprovado; OpenSpec estrito aprovado. Primeira execução anterior detectou somente a fixture administrativa sem e-mail verificado; a fixture foi corrigida, sem relaxar autenticação. O resultado final da execução intermediária não foi recuperado após expirar a sessão; somente a execução completa acima é usada como evidência.

A leitura do cliente revelou chave de cartão mantida na aba após recuperação com a mesma seleção/revisão. O delta/design/tasks foram atualizados antes da correção da UI: usar a revisão opaca da recuperação e vincular a chave à revisão da seleção, conservando idempotência em resultado incerto da mesma tentativa.

## Task 2.2

Ação Reabrir carrinho adicionada ao pagamento de cartão em Ver pedido e entrega no card da cliente de Vendas e pagamentos, uma vez por compra agrupada. Modal nativo com prévia de quantidade/total/meios disponíveis, motivo, reconhecimento explícito, foco/scroll restaurados ao cancelar e confirmação idempotente bloqueada durante envio. Repetição de rede conserva a decisão; conflito invalida a prévia e atualiza a lista. Confirmados não oferecem ação; reaberturas antigas exibem histórico. O refresh da ação recupera as páginas previamente carregadas usando os filtros atuais e preserva fotos expandidas.

O carrinho recarrega por foco; recuperação autorizada com seleção elegível descarta a chave antiga, mantém fotos selecionadas e permite PIX/cartão habilitados. Revisão nova usa chave nova; resultado incerto na mesma seleção conserva a chave. Respostas terminais atrasadas consultam de novo o carrinho, sem projetar bloqueio local obsoleto nem emitir outro pagamento automaticamente.

- Vitest dirigido: **38 aprovados em 3 arquivos, 9,71 s** (cart-recovery, cart-recovery-page, cart). A primeira coleta teve **37 aprovados/1 falha**, limitada ao seletor ambíguo da fixture com duas clientes; a consulta foi restrita ao card da cliente alvo. Não foi relaxada expectativa de produto.
- TypeScript --noEmit aprovado após os arquivos/testes da UI.
- Lint amplo, testes amplos, build e matriz PostgreSQL de integração estão em andamento em 3.1; não são declarados aprovados aqui.
