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

API/projeção e UI implementadas e validadas em 2.1/2.2/2.3/2.4. Gates locais e preparação do PR concluídos em 3.1. CI completo do head final e revisão humana permanecem gates externos antes da publicação. A instalação npm ci --ignore-scripts concluiu com lockfile existente; não houve atualização de dependências. O guia Next instalado use-client foi lido antes da UI.

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
- Matriz PostgreSQL ampla anterior a 2.3: **142 aprovados, 2 ignorados, 6 avisos, 1 erro de setup legado, 1210,90 s**. O erro em test_payment_shortcut_projection é o mesmo DROP de FK sem nome descrito acima, fora do caminho de produto. Essa execução não é tratada como suíte inteiramente verde. Seus casos de domínio/concorrência/checkout/confirmador/carrinho passaram; as projeções afetadas por 2.3 foram repetidas abaixo.
- API PostgreSQL atual, isolada e sem fixtures legadas: **13 aprovados, 6 avisos, 157,37 s**.
- Projeções/operações financeiras/disponibilidade em SQLite próprio temporário, conforme fixture do CI: **47 aprovados, 2 ignorados, 20 avisos, 233,60 s**. Inclui testes existentes de exportação, paginação, limites de consultas, pedidos pendentes legados e grupos financeiros, sem alterar testes legados para mascarar incompatibilidade PostgreSQL.
- Build final após 2.3 aprovado; lint final amplo **0 erros/34 avisos**, TypeScript e 97 testes afetados aprovados. Ruff amplo e validação estrita da change aprovados. Revisão do diff confirmou somente recuperação, guarda tardia, projeção/UI, testes/OpenSpec e inclusão dos casos PostgreSQL no passo de checkout do CI; dependências, migrations e PRs paralelos preservados.
- PostgreSQL sintético exclusivo foi parado após conferir ID/nome/label; nenhum recurso preexistente foi removido. Arquivo SQLite sintético temporário ficou fora do Git.
- PR draft **#265**, base codex/fix-cart-pending-payment-scope/c41e274 do #263, criado e anexado: https://github.com/conradodeita/markina-gallery/pull/265. Primeiro candidato funcional ef9f17338078b003aed89411b760b0775325fcab; CI inicial 39658351207. O head seguinte inclui a ampliação 2.4 solicitada pelo proprietário; acompanhar seu CI no PR, sem declarar aprovação com jobs pendentes. Resultados finais do CI serão registrados no corpo do PR, evitando uma sequência de commits documentais que reinicie todos os jobs.

## Task 2.4 — outras telas do fotógrafo

Ao esclarecer que o fotógrafo também não deve ver pedidos iguais, o proprietário motivou verificação focada dos consumidores do rascunho. Regressão antes da correção: **1 falha/12 desmarcados, 11,97 s**; o diretório contava 4 pedidos (2 originais + 2 rascunhos). A condição de visibilidade foi centralizada em app/order_visibility.py e aplicada somente ao painel financeiro, lista de pedidos da galeria e contador comercial do diretório. Contagem bruta, inventário, deletion_eligible, exclusão e reconciliação permanecem protegidos; o helper não participa de comandos de escrita. A lista da galeria também identifica o original como Carrinho reaberto.

- PostgreSQL focado após correção: **2 aprovados, 12 desmarcados, 6 avisos, 19,19 s**. Verifica ausência de rascunho em listas/contador, snapshots originais identificados, inventário bruto completo, seleção intacta e visibilidade após comunicação.
- API PostgreSQL completa final: **14 aprovados, 6 avisos, 118,46 s**.
- Regressões existentes do diretório/exclusão em SQLite próprio: **21 aprovados, 26 avisos, 115,96 s**, sem modificar suas expectativas. Preserva autorização, paginação, buscas, custo de consulta e exclusão protegida.
- Frontend afetado (galeria, clientes, pagamentos e histórico): **76 aprovados em 10 arquivos, 21,62 s**. Inclui três cenários novos da consulta da galeria; outros 97 afetados de carrinho/pagamento/entrega permanecem válidos para os trechos não alterados.
- Ruff amplo aprovado; eslint dirigido e TypeScript --noEmit aprovados; build Next final após 2.4 aprovado. OpenSpec estrito da change aprovado e validação global 1.14.0 repetida antes do commit final.
- Segundo PostgreSQL sintético exclusivo, ID 560d10a251e20a2abb464cd2f10c7d83d9fa23c9efb0eaa6abd1d0aafa5e0f91, foi parado após conferir ID/nome/label. Nenhuma escrita adicional foi feita no Oracle. A recuperação real e o rascunho e1d93b85 permanecem preservados até eventual publicação; esta change altera a projeção, não remove os dados reais.

### Publicação e rollback propostos (não executados)

1. Revisar/integrar #263 e este PR em main, com autorização de merge própria e checks finais concluídos; identificar o SHA integrado exato. #261/#262/#264 não são modificados por esta change.
2. Repetir inventário do alvo markina.pickyourpic.com.br, entrada 127.0.0.1:8080, API 8000/web 3000 internos, projeto markina-gallery em /opt/markina-gallery. Comparar configurações, imagens API/web e saúde; obter autorização operacional para esse SHA e rollback. Inventário read-only desta sessão observou API 57a6dd53b5f5, web a380cac2b174 e nginx ee8973e6551e; reconferir antes de qualquer ação.
3. Publicar API/web coordenadas pelo procedimento existente de release aprovado, sem migration, mudança de chave/configuração, workers ou infraestrutura compartilhada; recarregar somente o nginx próprio se exigido pelo procedimento.
4. Conferir saúde, negação sem sessão e UI com sessão legítima do proprietário: recuperação antiga identificada, rascunho sem duplicação e mesmas fotos no carrinho. Não criar checkout, pagar ou repetir recuperação real como teste sem autorização específica.
5. Se necessário e autorizado, voltar às imagens/API_VERSION anteriores, preservando banco e auditoria. Não restaurar backup ou desfazer uma recuperação depois de nova atividade da cliente; exception/cancelled/draft já são compreendidos pelo código publicado.

Sem merge, deploy, restart, migration ou escrita no Oracle nesta implementação. Esta funcionalidade exige API e web; não exige publicação de worker/cofre ou mudança na API InfinitePay. Links antigos não são cancelados remotamente. CI e revisão humana permanecem gates de publicação; aprovação técnica não equivale a autorização operacional.

## Correção do gate CI 39660195152

O CI do head 9f84756fa4d7e2e3f447f7305883717c3f93c229 terminou com falha no backend: **1 falha, 1758 aprovados, 32 ignorados, 698 avisos, 1962,27 s** na suíte ampla. O único teste reprovado foi test_reabertura_aparece_no_historico_e_rascunho_pix_nao_parece_compra_duplicada. A consulta interna do teste compara SaleOrder.payment_group_id (UUID) diretamente com a string retornada pelo JSON de /library/cart/prepare; o adaptador SQLite exige UUID e falhou em value.hex antes das verificações seguintes. A execução local anterior em PostgreSQL aceitava essa string, deixando a incompatibilidade do teste sem cobertura em SQLite.

Frontend, OpenSpec, gitleaks, ci-scope, runtime-images e gemma-runtime passaram. O gate homolog-inventory-policy recusou o backend reprovado; os passos PostgreSQL posteriores à suíte ampla e todos os jobs de deploy foram ignorados. Esse run não comprova aprovação final nem execução das regressões PostgreSQL no CI.

Task 3.2: a falha foi reproduzida em SQLite sintético fora do Git (**1 falha, 7 avisos, 14,54 s**). A comparação da consulta de teste agora converte o identificador JSON com UUID(group_id), sem alterar o identificador HTTP nem qualquer expectativa de produto. A suíte completa da API em SQLite passou: **14 aprovados, 20 avisos, 138,58 s**, incluindo histórico, rascunho PIX, listas/contador do fotógrafo, preservação da seleção e comunicação posterior. Ruff amplo aprovado; OpenSpec 1.14.0 global: **132 aprovados, 0 falhas**; diff sem erros de whitespace. Nenhum código de aplicação foi alterado nessa correção, portanto os resultados anteriores de frontend e os contratos já validados permanecem evidência para seus trechos inalterados. O novo CI completo continua obrigatório.

O proprietário instruiu o executor a parar o acompanhamento depois do push; ele acompanhará o novo run e trará o resultado. Identificar o head e o resultado futuro pelo próprio PR #265. Não presumir CI verde nem realizar merge, deploy ou operação real enquanto esse gate e as autorizações correspondentes estiverem pendentes.

## CI aprovado e preparação de publicação autorizada — 21/10/2026

O proprietário retomou o acompanhamento. CI 39666630350 do head 6f4a903253d4c632863d73f0f2a5fc05589672da concluído success: backend amplo **1759 aprovados, 32 ignorados, 698 avisos, 1922,20 s**; PostgreSQL checkout/reabertura **45 aprovados**, concorrência multi-tenant **4 aprovados** e inventário de exclusão **1 aprovado**. Frontend **586 aprovados em 66 arquivos**, build aprovado; OpenSpec **132 aprovados**; ci-scope, gitleaks, gemma-runtime, runtime-images e homolog-inventory-policy aprovados. Os oito jobs de validação passaram; todos os jobs de deploy foram ignorados. Em seguida, o proprietário declarou: “Autorizado o deploy”.

Preflight oficial somente-leitura no checkout/alvo então publicado 5446cf4d7328ef6283ebfab50b5d1976d561fc8d confirmou host clearbudget-vnic, projeto markina-gallery, domínio markina.pickyourpic.com.br, bind nginx 127.0.0.1:8080, schema 20261017_0084 e HTTPS de healthz/api-health/web. API saudável: imagem sha256:1eecc29b45863932f64b38bb38ca8da3428da62797f4bd63109bdcd937c06d2f; web saudável: sha256:5758496e8a0e03996232e1b390a24268a876b22a3c81b6209aa38c1356c416d7. Consulta adicional confirmou 15 serviços próprios saudáveis, 62 GB livres e ausência de marcador in-flight. Nenhuma mutação remota foi executada. O fingerprint desse inventário é do alvo antigo e não pode ser usado para publicar o novo SHA.

O gate de escopo recusou localmente a comparação 5446cf4d..6f4a903 com api_fora_do_escopo. Duas regressões novas reproduziram ausência de dez runtimes e dos cinco testes frontend exatos (**11 falhas em subcasos**). A allowlist agora inclui somente esses dez runtimes; o manifesto fixa seus blobs do mesmo código já validado, atualiza os três blobs existentes alterados e avança a baseline para o SHA saudável observado. Os cinco testes são permitidos nominalmente, sem prefixo genérico. Docker/Compose, wrappers, scripts de deploy, schema, segredos, dependências e código de aplicação não mudaram nessa preparação.

Validações da preparação: **17 testes de escopo aprovados, 81,174 s**; **13 testes de classificação aprovados, 4,215 s**; política completa do workflow aprovada; Ruff dos três scripts afetados aprovado; OpenSpec 1.14.0 global **132 aprovados, 0 falhas**. A política de workflow inicialmente apontou a baseline antiga fixada no teste; a expectativa foi atualizada para 5446cf4d, conforme o preflight real, preservando a comparação exata. O verificador local passou a retornar app_release_ready=true/somente_api_web para o candidato de aplicação. Esses resultados não substituem CI do novo head nem inventário/proteção do SHA integrado.

Próxima etapa: enviar a preparação ao mesmo PR, revisar a integração de #263/#265 sem modificar #261/#262/#264 e acompanhar o CI do candidato/integrado. O release oficial permanece condicionado ao inventário/fingerprint novo e aprovação protegida específica, conforme a spec add-production-app-release-workflow. Somente API/web serão recriados, com preservação das imagens anteriores; não se executam pagamentos reais nem recuperação financeira como teste.

## Tasks 3.4/3.5 — integração e publicação concluídas em 21/10/2026

Esta seção substitui as pendências de integração/publicação dos checkpoints históricos acima. O PR #265 foi integrado por merge regular em `21b89c332c6937b7079679888d52bd6a8aefe25d`, com pais `5446cf4d7328ef6283ebfab50b5d1976d561fc8d` e `575e44a0b3ef4348856ee66ef1ec4ae47bcdf2a8`. O GitHub reconheceu o PR #263 como integrado por ancestralidade. A árvore `0092b9be97b69f5e49b68dd928a3c537369f5676` é idêntica à do candidato aprovado; não houve reescrita de commits, bypass ou merge de #261/#262.

- CI do head 575e44a: [39674012325](https://github.com/conradodeita/markina-gallery/actions/runs/39674012325), oito jobs de validação success; backend 1759 aprovados/32 ignorados, PostgreSQL 45 checkout/reabertura, 4 concorrência e 1 exclusão. Nenhum deploy nesse run de PR.
- CI integrado: [39679561004](https://github.com/conradodeita/markina-gallery/actions/runs/39679561004), concluído success no SHA 21b89c3. Backend: **1759 aprovados, 32 ignorados, 698 avisos, 2013,00 s**. PostgreSQL: **4 aprovados/11,98 s** em concorrência, **45 aprovados/124,13 s** em checkout/reabertura e **1 aprovado/2,51 s** em exclusão. Frontend: **586 aprovados em 66 arquivos**, build aprovado, lint 0 erros/34 avisos preexistentes. OpenSpec: **132 aprovados/0 falhas**. Gitleaks, Gemma, runtime-images e homolog-inventory-policy aprovados.
- Classificador: escopo app. [Preflight oficial](https://github.com/conradodeita/markina-gallery/actions/runs/39679561004/job/119516227475) success, app_release_ready=true; inventário do alvo 21b89c3 sobre checkout 5446cf4d, API/web saudáveis, schema 20261017_0084 e HTTPS 200. Fingerprint aprovado: `42da3d160f1a2d64ff74f7f0f4d16633a2f637c0c14689a1e0f497586af45001`.
- O histórico de revisão do run registra **production/approved por conradodeita**. O agente não contornou a proteção nem aprovou o ambiente por CLI. [Release oficial](https://github.com/conradodeita/markina-gallery/actions/runs/39679561004/job/119516351250) success: início 22:13:57 UTC, recibo saudável 22:15:31 UTC (19:15:31 em São Paulo), fim do job 22:15:33 UTC.

### Inventário e preservação

Alvo: clearbudget-vnic/132.145.193.169, /opt/markina-gallery, projeto markina-gallery, https://markina.pickyourpic.com.br, bind nginx 127.0.0.1:8080; API 8000/web 3000 permanecem internos. Preparação autorizada obteve os objetos de main por git fetch. O backup antigo de manutenção foi preservado reversivelmente em `/var/lib/markina-gallery/deploy-state/app-nginx-maintenance-before-21b89c332c6937b7079679888d52bd6a8aefe25d.conf`, sob lock global, após conferir identidade, ausência de tentativa/marker, imagens/saúde e igualdade com nginx ativo. Arquivo 0644/644 bytes, SHA-256 `4dee6b0c7c8278f6a9b827261c25d3215c9ea8955e41ff7fe3eabdd5297edce7`; sem sobrescrita ou edição de configuração ativa nessa preparação.

O workflow utilizou o helper emergencial já aprovado, preservou as imagens antigas, homologou o candidato ARM64 isolado e recriou somente API/web com --no-deps. A manutenção preservou o retorno financeiro e devolveu 503 nos demais ingressos durante a troca; o procedimento não instalou resposta de sucesso fictício para eventos não persistidos. Ao concluir, nginx voltou ao mesmo hash anterior; não restaram marcadores de manutenção/tentativa. Nenhuma migration, segredo/configuração financeira, compra, seleção ou pagamento real foi alterado pela operação.

| Serviço | Imagem preservada de 5446cf4d | Imagem publicada em 21b89c3 |
| --- | --- | --- |
| API | sha256:1eecc29b45863932f64b38bb38ca8da3428da62797f4bd63109bdcd937c06d2f | sha256:92bcf8652e1932fbd3b2d6c7bcbd0c7006f0012cfe686d4eb6aa95e6eec139a5 |
| Web | sha256:5758496e8a0e03996232e1b390a24268a876b22a3c81b6209aa38c1356c416d7 | sha256:c1be0a0128c87ef756abde0a4343a8a9331defa84ca00645704d17e71d71bbb2 |

Consulta posterior somente-leitura confirmou checkout, APP_VERSION e app-last-healthy em 21b89c3, schema **20261017_0084**, API/web saudáveis e HTTPS **200 em /healthz, /api/health e /**. GETs sem sessão para /api/admin/clients, /api/admin/settings/infinitepay e /api/library/cart retornaram **403**. Os 14 containers fora de API/web têm Created/StartedAt anteriores ao início do job de release; nenhum foi recriado/reiniciado por essa publicação. Os 15 serviços em execução estão healthy; o container existente migrate está encerrado com exit 255 e Created/StartedAt anteriores ao job, sem participar do procedimento. Ele foi preservado e nenhuma migration foi executada.

Recibo app-api-homologation.json: distribution_comparison=passed e arm64_startup=passed. A API ativa confirmou **Python 3.13.16**, aiohttp **3.14.4**, multidict **6.9.1**, urllib3 **2.8.0** e yarl **1.25.1**, iguais à imagem anterior; nenhuma manutenção de outros consumidores foi executada. app-previous.sha e os dois IDs de rollback correspondem às imagens de 5446cf4d da tabela. Não foi necessário rollback nem restauração de banco.

### Limites e ação do proprietário

Transação READ ONLY após o release confirmou a configuração da própria conta ativa/v5: api_key_configured=true, card_enabled=false, card_available=false, pix_available=true; rollback da transação ao terminar. O proprietário decidiu habilitar cartão pela UI somente depois do deploy e foi avisado após a confirmação de saúde. A API Key existente foi preservada; não solicitar recadastro, não habilitar por SQL/CLI e não criar checkout real como teste.

Não houve validação visual com sessão do proprietário/cliente, novo pagamento real, nova recuperação das compras eae11005/e2194ce5/11f18369 nem cancelamento remoto de links antigos. Esses limites não são resultados de teste aprovados. A implantação disponibiliza a ação auditada Reabrir carrinho e as projeções já validadas pelo CI. A gestão de credenciais pelo próprio fotógrafo continua no PR #262, como seguimento separado; sua migration/keyring não fizeram parte deste release. Sincronização/arquivo da change continua sujeita à revisão humana.
