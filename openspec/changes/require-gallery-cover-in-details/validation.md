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
