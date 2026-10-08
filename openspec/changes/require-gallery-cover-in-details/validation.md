# Validation

## Decisão e inventário — 08/10/2026

- O proprietário pediu obrigatoriedade de capa e delegou a decisão da etapa, exigindo preservar o cadastro inicial.
- Decisão: etapa 3, Detalhes, que já concentra upload e configuração da capa. O salvamento dessa etapa e a conclusão guiada passam a exigir capa configurada pronta; cadastro inicial, Ajustes e Vendas continuam permitidos.
- Inspeção do fluxo existente: criação persiste dados essenciais antes de upload; registro de capa exige UUID da galeria; saveVisualSettings usa o PATCH geral de settings; backend não verifica a capa antes desse salvamento; editor usa somente cover_photo_id para marcar etapa completa; Concluir é link ao resumo, sem estado persistente.
- Não foi modificada galeria real, capa, vínculo, permissão, configuração ou infraestrutura. Galerias atuais sem capa conservam acesso conforme as regras vigentes.

## Estado

Proposal, delta spec, design e tasks preparados para revisão. Nenhum código alterado, teste de aplicação executado, task implementada, commit, PR ou deploy nesta change. O fluxo openspec-propose exige apresentar o planejamento e aguardar nova instrução de aplicação; não iniciar código nesta fase.

`npx.cmd --yes @fission-ai/openspec@1.14.0 validate require-gallery-cover-in-details --strict`: aprovado. Status de planejamento completo com os quatro artefatos presentes; isso não comprova implementação.


## Implementação autorizada e evidências locais — 08/10/2026

O proprietário aprovou implementar capa, prévias e orientação OTP, e depois push/merge/deploy. A capa é entregue em commit separado; CI/publicação são gates do pacote aprovado. A nota de planejamento acima registra o estado anterior, substituído por esta seção.

Contrato: editor e Detalhes expõem `cover_readiness={status,message}` (`missing`, `processing`, `failed`, `ready`); editor oferece `actions.can_complete`. A mesma decisão valida capa configurada, ownership, galeria/pasta e admin_preview ready com caminho persistido seguro. Não há fallback para outra foto. O PATCH de settings rejeita com 409 qualquer campo de título/capa sem prontidão, antes de alterar dados ou auditar sucesso. Campos não visuais continuam disponíveis. Concluir consulta o editor atual e só navega após prontidão; não persiste publicação nem modifica autorização de clientes.

- Backend, banco SQLite descartável fora do repositório: `python -m pytest -q tests/test_required_gallery_cover.py tests/test_gallery_workflow_remediation.py tests/test_tenant_configuration.py --tb=short`: **43 passed**, 148,25 s. Cobertura de estados, referências antigas/incompatíveis, caminho inválido, salvamento atômico/auditoria, cadastro e upload sem capa, troca preservando foto anterior e vínculos ativos; regressões de capa e configuração multitenant. Warnings preexistentes de startup e ciclo FK na limpeza da fixture SQLite.
- Frontend: `npm.cmd test -- app/admin/galleries/gallery-cover-required.test.tsx app/admin/galleries/gallery-editor.test.tsx`: **63 passed**, 9,57 s; estados e conclusão com leitura nova, falha HTTP e rejeição de estado antigo. Fixture positiva de configuração atualizada para capa pronta, sem exceção na regra.
- Ruff app/tests: aprovado. ESLint: 0 erros/37 warnings preexistentes. Typecheck e Next 16.3.2 build: aprovados, incluindo CSS final.
- OpenSpec 1.14.0 estrito: aprovado; diff-check limpo.
- QA visual local: DOM exportado do componente real após render de fixture sintética, estilos reais e escopo admin-frame, Chrome headless a 390/1440 px. Sem transbordamento horizontal (scrollWidth igual ao viewport); mensagem de obrigatoriedade e upload visíveis; Salvar desabilitado e diferenciado visualmente. Artefatos temporários fora do Git. Isso não é ensaio autenticado remoto nem aceite humano de homologação.
- Na primeira execução, fixtures novas usaram estado inválido e tentaram persistir referências que FKs existentes proíbem. Corrigidas para queued e projeções defensivas sem violar FKs; nenhuma restrição do banco foi relaxada. Registro/upload de capa separado do PUT JPEG real respeitado nos testes.

Sem migration, preenchimento automático, revogação, limpeza de fotos/clientes, alteração de segredo ou recurso de terceiros. Aceite visual remoto, sincronização e archive permanecem posteriores à entrega/revisão humana. Piloto A+B não foi validado nesta implementação.


## Entrega iniciada — 08/10/2026

Pacote enviado à PR #145: https://github.com/conradodeita/markina-gallery/pull/145 . HEAD caf5395341eaf48dea3e605a1860bb1fb8236b84, base develop af5b3a695f82a4493dcd7d99123da62599926633. CI 37786297481: https://github.com/conradodeita/markina-gallery/actions/runs/37786297481 . Frontend, OpenSpec e gitleaks aprovados; backend ainda em execução na última leitura. Nenhum merge ou deploy deste pacote realizado até aqui.

Autorização de push/merge/deploy permanece válida para este pacote. Após CI integral verde, reconferir HEAD/base/inventário/filas e integrar somente o HEAD aprovado; não pedir autorização novamente. Merge dispara CI/deploy de develop. Confirmar deploy-homolog SUCCESS, merge SHA no Oracle, schema 20261001_0071, saúde/endpoints e IDs dos terceiros antes de declarar publicado. Tasks de entrega permanecem pendentes até evidência. Não arquivar/sincronizar sem revisão humana; não antecipar limpeza ou ensaio A+B.


## CI aprovado e merge — 08/10/2026

CI 37786297481 concluído SUCCESS em 08/10/2026 às 14:04:29 UTC; backend, frontend, OpenSpec e gitleaks SUCCESS. Preflight repetido: Oracle limpo no baseline af5b3a6, schema 20261001_0071, 13 serviços próprios healthy e mesmas filas sem pendências (814 media completed; 844 facial completed/8 cancelled; 27 whatsapp expired; lifecycle vazio).

PR #145 integrada após gates/autorização em 08/10/2026 às 14:06:48 UTC. Merge SHA abc994bf9e7cc01d616b27f7acd0d3a0011d807b. O workflow de develop ainda precisa aprovar CI e concluir deploy-homolog; merge não comprova publicação. Acompanhar o run desse SHA e verificar remotamente antes de encerrar a entrega técnica.


Workflow de publicação do merge: https://github.com/conradodeita/markina-gallery/actions/runs/37789805938 . Run 37789805938 em execução para abc994bf9e7cc01d616b27f7acd0d3a0011d807b. Sem trailers de limpeza; manutenção posterior deve ficar inventory. Não iniciar deploy paralelo nem declarar versão publicada apenas pela integração da PR.

## Publicação verificada — 08/10/2026

PR #145: https://github.com/conradodeita/markina-gallery/pull/145 . Workflow develop 37789805938 SUCCESS, incluindo deploy-homolog concluído às 14:43:14 UTC (11:43:14 America/Sao_Paulo): https://github.com/conradodeita/markina-gallery/actions/runs/37789805938 . Oracle no merge SHA abc994bf9e7cc01d616b27f7acd0d3a0011d807b, Git limpo, 13 serviços próprios healthy e endpoints healthz/api health HTTP 200. Hashes dos dois módulos backend conferem com o código publicado; chunks web contêm cover_readiness, orientação OTP condicional e contrato history|purchases.

Schema permanece 20261001_0071. Filas: media 814 completed; facial 844 completed/8 cancelled; whatsapp 27 expired; lifecycle vazio. IDs dos seis containers de terceiros conferem com o inventário anterior. SHA256 de docker/.env.homolog permanece 11a743934ce1fec40c7419ec48764b1b87fc233b9b2a8fb96b88d50b20951c07; conteúdo não exposto. Sem limpeza ou migration neste pacote.

Gate homolog aprovado pela conta conradodeita conforme histórico GitHub; nossa tentativa concorrente de POST retornou 422 por ausência de solicitação pendente e não realizou a aprovação. Entrega técnica concluída; aceite visual autenticado humano, ensaio A+B, sincronização e arquivamento continuam separados.

Nova instrução permanente do proprietário: após CADA push, parar e aguardar sua resposta sobre CI verde ou falha antes de prosseguir. O merge/deploy acima precedeu essa instrução. Recibos finais registrados localmente, sem novo push nesta rodada.

## Refinamento editorial — 08/10/2026

Solicitação explícita do proprietário: retirar o parágrafo “Envie do seu dispositivo um JPEG horizontal (largura maior que a altura), sem marca-d’água nem grade, para usar como capa. As fotos das pastas não são carregadas nesta etapa.”. Registrada em proposal/design/delta/tasks antes da alteração. Diff funcional: apenas exclusão desse parágrafo em gallery-editor.tsx; upload, validações e estados existentes preservados.

Validação no baseline abc994bf9e7cc01d616b27f7acd0d3a0011d807b: duas suítes existentes do editor, 63 testes aprovados em 30,02 s; ESLint do componente com 0 erros/4 avisos preexistentes de img; TypeScript noEmit e build Next 16.3.2 aprovados; OpenSpec 1.14.0 da change estrito aprovado; diff-check limpo. Nenhum teste novo nem alteração backend. Aceite visual remoto ainda pendente.

Branch feature/remove-gallery-cover-help. Autorização anterior de entrega do trabalho mantida; após o push, parar e aguardar o proprietário informar o resultado do CI, sem polling, merge ou deploy antecipados. Limpeza e ensaio remoto A+B não realizados.
