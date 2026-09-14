# Continuidade

Atualização operacional de 14/09/2026: modo escuro/capas e rebrand publicados pelo PR #83, SHA `23bdee9bb7b3c1f946693f08c48741dee28188f1`, pipeline `34841907861` aprovado. Worker opcional atualizado no mesmo checkout; migração 0055 já estava aplicada. Ver `../rebrand-pick-your-pic/deployment-result.md` para evidências e bloqueio de arquivos de branding ausentes em armazenamento não persistente. Os parágrafos abaixo são o estado histórico anterior ao deploy, não uma autorização pendente atual.

Implementação local concluída e validada em 14/09/2026. Todas as tarefas locais reconciliadas; evidências em validation.md. Tema compartilhado, capas limpas autorizadas e validação horizontal implementados. Não houve operação remota. O rebrand autorizado pode seguir agora.

O pedido de rebrand está registrado separadamente em `rebrand-pick-your-pic`. Ordem: aplicar e validar modo escuro/capas, depois rebrand, respeitando os requisitos próprios. Não misturar aprovação de proposta, implantação e validação humana.

Base: `origin/develop` no merge PR #82, `eb8c0837e3144f8d27429dffc05bb3683169d59a`. A publicação dessa base permanece pendente da confirmação operacional após inventário; o commit documental `c49118d` na branch `codex/gallery-preview-exposure-and-installable-ui` preserva o plano e o estado remoto. Nenhuma operação remota foi feita durante o planejamento das novas changes.

Pontos localizados para implementação: import_photo_source/set_parent_gallery_cover, resolvedores de capa e parent_gallery_details em backend/app/main.py; testes de capa em test_gallery_workflow_remediation.py/test_derived_galleries.py. A prévia admin_preview já é limpa e limitada. CSS compartilhado ainda contém cores literais. Executar testes backend somente com DATABASE_URL apontando banco temporário explícito: as fixtures recriam tabelas.
