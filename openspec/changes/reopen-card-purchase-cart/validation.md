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

## Task 2.3 — aparência de duplicação

O proprietário apontou os pedidos c648edb4/e1d93b85 e reafirmou que a cliente não deve perder a seleção. Oracle foi acessada somente com SELECT em transação READ ONLY, sem sessão de cliente: c648edb4 está cancelled, vinculado à eae11005 em exception com recuperação auditada; e1d93b85 é pending, sem frozen_at/confirmed_at/ProviderPayment, associado a PaymentGroup draft. Ambos têm 22 fotos/R$154; as 22 fotos continuam selecionadas. Os 15 serviços próprios permaneciam healthy na consulta de inventário. Nenhum registro, segredo, serviço ou checkout real foi alterado.

Regressão sintética antes da correção: **1 falha, 12 desmarcados, 15,45 s**, pois a preparação do PIX tornava 4 pedidos visíveis onde só havia 2 originais; os outros 2 eram rascunhos da mesma seleção. Após a correção: **1 aprovado, 12 desmarcados, 19,43 s**, comprovando omissão do rascunho, seleção preservada, histórico de reabertura da própria cliente e promoção da nova compra somente após informar PIX. A consulta mantém pedidos legados sem grupo, comunicações, confirmados e registros removidos.

Projeção da cliente e UI de Compras agora indicam Carrinho reaberto, Abrir carrinho e seleção devolvida; não exibem o aviso genérico de conferência nem a URL antiga para o caso auditado. O card administrativo também identifica a reabertura. Rascunho interno não é excluído nem publicado como outra compra no painel financeiro; fotos continuam em Seleções em aberto. Remover fotos pelo acesso da cliente apagaria a seleção, portanto não é procedimento de recuperação.

Vitest afetado final: **97 aprovados em 10 arquivos, 41,65 s**, incluindo histórico/entrega e painel completo. TypeScript --noEmit, build Next 16.4.2 e lint amplo aprovados (**0 erros, 34 avisos preexistentes**). Uma primeira coleta teve 52 aprovados/1 falha por seletor textual que passou a encontrar também o novo badge; o teste foi limitado à mensagem de confirmação esperada. O lint inicial detectou leitura de ref durante render do novo modal; a decisão idempotente passou a state, preservando a chave e o motivo no reenvio, sem supressão da regra.

## Checkpoint 3.1

- Suíte frontend ampla anterior ao acréscimo do histórico: **582 aprovados em 65 arquivos, 166,34 s**. Reutilizada junto aos 97 afetados finais; o CI repetirá a suíte completa no candidato.
- Ruff amplo backend/app e backend/tests aprovado. OpenSpec 1.14.0 (mesma versão fixada no CI): **132 aprovados, 0 falhas**; change atual aprovada novamente após 2.3. O CLI global 1.14.1 promove avisos existentes de textos longos e retornou 102/30; não foi usado como evidência de aprovação nem motivou alterações fora do escopo.
- Um comando misto em PostgreSQL passou os 13 casos atuais da API e o primeiro caso legado (14 aprovados), mas falhou no setup legado seguinte em Base.metadata.drop_all: FK use_alter sem nome não permite DROP CONSTRAINT no PostgreSQL. Esse comando não é declarado aprovado. As fixtures novas usam schemas isolados; as regressões legadas estão sendo repetidas em SQLite temporário, como no CI, e a API isolada está sendo repetida separadamente.
- A matriz PostgreSQL ampla iniciada antes de 2.3 e as repetições acima ainda não terminaram; resultado final/CI do novo PR pendentes. O passo de checkout PostgreSQL do CI foi estendido para rodar todos os novos casos, sem alterar dependências ou gates Python.

### Publicação e rollback propostos (não executados)

1. Revisar/integrar #263 e este PR em main, com autorização de merge própria e checks finais concluídos; identificar o SHA integrado exato. #261/#262/#264 não são modificados por esta change.
2. Repetir inventário do alvo markina.pickyourpic.com.br, entrada 127.0.0.1:8080, API 8000/web 3000 internos, projeto markina-gallery em /opt/markina-gallery. Comparar configurações, imagens API/web e saúde; obter autorização operacional para esse SHA e rollback. Inventário read-only desta sessão observou API 57a6dd53b5f5, web a380cac2b174 e nginx ee8973e6551e; reconferir antes de qualquer ação.
3. Publicar API/web coordenadas pelo procedimento existente de release aprovado, sem migration, mudança de chave/configuração, workers ou infraestrutura compartilhada; recarregar somente o nginx próprio se exigido pelo procedimento.
4. Conferir saúde, negação sem sessão e UI com sessão legítima do proprietário: recuperação antiga identificada, rascunho sem duplicação e mesmas fotos no carrinho. Não criar checkout, pagar ou repetir recuperação real como teste sem autorização específica.
5. Se necessário e autorizado, voltar às imagens/API_VERSION anteriores, preservando banco e auditoria. Não restaurar backup ou desfazer uma recuperação depois de nova atividade da cliente; exception/cancelled/draft já são compreendidos pelo código publicado.

Sem merge, deploy, restart, migration ou escrita no Oracle nesta implementação. Esta funcionalidade exige API e web; não exige publicação de worker/cofre ou mudança na API InfinitePay. Links antigos não são cancelados remotamente. CI e revisão humana permanecem gates de publicação; aprovação técnica não equivale a autorização operacional.
