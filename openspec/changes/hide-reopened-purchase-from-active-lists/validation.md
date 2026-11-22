# Validation

## Contrato backend

A regressão de ocultação falhou antes do ajuste: a resposta de Compras ainda continha provider_payment_groups após reabertura (1failed/7deselected). Após a correção,8testes PostgreSQL sintéticos aprovados em61,82s,6avisos de depreciação FastAPI. Cenários: ocultação imediata sem remoção das fotos, remoção de todos os grupos por HTTP mantendo histórico, filtro administrativo/CSV, cliente alheia, nova compra, confirmado sem reabertura e retornos queued/processing/verified/failed. Aplicação real de resultado sintético verified no guard existente produz receipt ignored; a ocorrência continua visível para conferência, sem confirmar pedidos cancelados.

Usado somente container local exclusivo pyp-vault-ownership-test-20261021, ID/label verificados antes de iniciar,127.0.0.1:15470/pyp_photographer_test. Nenhum acesso Oracle, dado real, API InfinitePay, segredo operacional, merge ou deploy. A compra673ba102 não foi consultada nem alterada; seu relato orientou a regressão sintética.

Ajustadas as expectativas antigas de exibição em três testes HTTP de recuperação conforme a decisão substitutiva aprovada; inventário, proteção de exclusão e pedidos legados mantêm seu contrato anterior. Suíte ampliada ainda pendente.

## Interface

A primeira tentativa de editar testes usou diretório frontend para paths a partir da raiz e não alterou arquivos;17testes antigos passaram nesse checkpoint, sem validar a melhoria. Após registrar efetivamente as regressões novas:4falhas/15passes antes do runtime. Depois:29testes aprovados/3arquivos em8,45s, incluindo filtro de histórico, refresh após reabrir sem card antigo, segunda página preservada, evidência tardia, ausência de checkout/ações financeiras/entrega no histórico. Ruff backend/app backend/tests e diff--check aprovados.

## Integração local

- Matriz PostgreSQL recuperação/domínio/API/visibilidade/credenciais:58aprovados,6avisos,469,96s, antes do reforço de estados incompatíveis. Nenhuma regressão financeira ou de concorrência.
- Frontend completo:67arquivos/612testes aprovados170,56s no checkpoint inicial; há repetição do candidato final com casos adicionais de estados incompatíveis.
- Lint:0erros/34avisos preexistentes. Primeiro build compilou, mas recusou fixture do teste novo cujo reopened_at foi inferido exclusivamente null; tipo da fixture corrigido para CartRecoveryStatus. Depois,19testes direcionados e build/TypeScript aprovados; ajustes posteriores de mensagens exigem repetição final.
- OpenSpec1.14.0:135aprovados/0falhas. Ruff backend/app backend/tests aprovado. Política de release técnica:publication_candidate_ready=false/api_fora_do_escopo, como esperado para cofre0085;7testes reais de política aprovados55,799s. O manifesto0084 e os gates de produção não foram ampliados.

## Manutenção proporcional

Reutilizada a projeção cart_recovery_statuses para histórico/conferência; o filtro financial_status da listagem passou a reutilizar o alias Literal já existente na exportação, removendo duplicação de enum no escopo. Substituídas mensagens e ações do histórico reaberto conforme novo contrato. Guards, mutation paths, ownership, modelos/migrations, configuração e endpoints financeiros preservados. Sem oportunidade segura de limpeza adicional; os componentes de fotos, cancelamento, auditoria, retomada válida e histórico legados continuam tendo consumidores.

## Limites operacionais

Cadastro real do cofre e publicação dependem do plano0085 do PR262. Esta melhoria sem schema só muda API/web, mas sua branch integrada contém0085; não usar o workflow0084 para publicá-la. Nenhuma autorização de publicação inferida de testes ou do pedido para continuar roadmap. Retornos sem evidência financeira não são resolvidos automaticamente; permanecem regidos pela recuperação manual auditada existente.

Reforço de estados incompatíveis:matriz HTTP25casos terminou24passes/1falha de fixture:consulta ao carrinho usava a sessão anterior ao helper que cria novo login da mesma cliente. create_session rotaciona sessões por subject/tenant/role; corrigido o teste para autenticar novamente antes da consulta, preservando autenticação e expectativas. Nenhum defeito de produção ou alteração de sessão aplicada. Casos finais incluem estado antigo incoerente sem URL retomável, carrinho vazio após confirmação tardia e reprocessamento de receipt antigo.

## Candidato final local

- PostgreSQL: os 12 cenários finais passaram em 161,65s, com 6 avisos de depreciação, após corrigir a fixture de sessão. Incluem receipt antigo ignorado que reaparece somente após novo processamento, confirmação tardia com carrinho vazio e estados awaiting_payment/verification_required/hold incompatíveis com a recuperação sem URL antiga exposta. Os 24 outros casos HTTP do checkpoint anterior passaram; a matriz anterior de58 casos cobre também domínio/concorrência/credenciais, conforme suas premissas registradas.
- Frontend: 67 arquivos / 616 testes aprovados em 171,55s no código final. Também cobre resposta sem marcador de conferência: conserva a ocorrência visível até a API conseguir classificá-la explicitamente.
- A suíte de135 itens OpenSpec e Ruff são repetidas no fechamento. Build/lint finais registrados após conclusão, antes do commit/push. CI remoto do novo head é requisito separado.

Fechamento: lint final sem erros (34 avisos preexistentes); build final e TypeScript aprovados. Ruff de backend/app e backend/tests aprovado; OpenSpec1.14.0 global135/0 e diff--check aprovados. PostgreSQL sintético exclusivo parado após o último teste, com ID/label novamente conferidos; sem remoção/prune. Revisão do diff confirma somente projeções, UI, testes, passo PostgreSQL do CI e artefatos relacionados; sem modelos, migrations, endpoints de escrita financeira, segredos ou PR261. A política operacional real continua recusando o cofre, sem ampliar o manifesto0084.

## CI final do candidato funcional

[CI #784](https://github.com/conradodeita/markina-gallery/actions/runs/39703967030), head `7b8f3039d931d88224304736d8a794beb2961f14`: **completed/success**, todos os jobs necessários concluídos, sem falhas ou pendências. Inclui backend integral e passo PostgreSQL com os novos testes, frontend, imagens nativas AMD64/ARM64, Gemma, scanner, OpenSpec e política agregadora. [CI #783](https://github.com/conradodeita/markina-gallery/actions/runs/39702759942) de266 também completo/success.

GO técnico para revisão e solicitação de autorização de integração; PRs continuam draft e não foram mesclados. Publicação operacional continua NO-GO até os requisitos de0085 do release-plan, inventário/backup/keyring/restore e autorização específica. Nenhuma compra real (incluindo673ba102), segredo ou recurso Oracle foi alterado nesta missão. A cliente pode remover todas as fotos sem eliminar rastreabilidade; somente ocorrência de conferência tardia reaparece, sem checkout antigo retomável.

O fechamento posterior somente documental conserva o runtime validado. Resultado exato dos checks desse head será registrado nos corpos dos PRs; não criar commits recursivos apenas para citar o próprio SHA. Specs principais não sincronizadas e changes não arquivadas, conforme gate de revisão humana.
## Reconciliação da projeção após a aposentadoria da InfinitePay

A evidência acima do CI #784 pertence ao commit 7b8f3039d931d88224304736d8a794beb2961f14, anterior à aposentadoria da InfinitePay em 22391e3a1f3beb60bfb7ba5b501d515e678e011c (#267). A aposentadoria removeu a projeção de recuperação junto com as rotas de escrita. Esta revisão restabelece apenas a classificação de histórico exigida pela decisão atual; não restaura checkout, chamadas ao provedor, emissão, confirmação ou reabertura.

- A função somente leitura em backend/app/provider_payment_history.py consulta os dois formatos preservados de evento de auditoria e recibos do mesmo tenant. Ela marca para conferência recibos queued/processing/verified, recibos processados após a recuperação (inclusive antigos reprocessados), NSU, confirmação ou estado financeiro incompatível.
- Compras omite apenas a tentativa auditada em exception sem evidência de reconciliação. Retornos tardios permanecem visíveis, sem URL de checkout; o filtro administrativo financial_status=reopened separa o histórico da lista ativa e também se aplica à exportação.
- A interface identifica a conferência tardia e oculta ações de entrega para pedidos reabertos ainda não confirmados. A aposentadoria das rotas e ações de InfinitePay continua intacta.
- Regressão sintética atual: backend/.venv/Scripts/python.exe -m pytest -q tests/test_payment_operations_redesign.py::test_retired_provider_recovery_is_history_only_and_never_reopens_checkout — 1 passed, 7 warnings. Cobriu formatos novo/legado de auditoria, recibo ignored antigo, receipt failed reprocessado após a recuperação, estados queued/processing/verified, NSU, estado incompatível, confirmação, ausência de evento, filtro do fotógrafo, exportação e ausência de mutação.
- Interface: vitest run app/admin/payments/page.test.tsx app/library/library.test.tsx — 2 arquivos, 36 testes aprovados.
- Ruff nos três arquivos Python alterados e tsc --noEmit no frontend passaram.
- git diff --check passou; Git reportou apenas avisos preexistentes de conversão LF/CRLF.
- OpenSpec global strict após esta reconciliação: 188/188 (157 changes e 31 specs), zero falhas.
