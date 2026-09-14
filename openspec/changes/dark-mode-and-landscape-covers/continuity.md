# Continuidade

Planejamento completo e validado. A implementação ainda não foi iniciada: nenhuma tarefa de código ou teste foi marcada como concluída. A solicitação adicional de rebrand chegou durante o inventário inicial de capas.

O pedido de rebrand está registrado separadamente em `rebrand-pick-your-pic`. Ordem: aplicar e validar modo escuro/capas, depois rebrand, respeitando os requisitos próprios. Não misturar aprovação de proposta, implantação e validação humana.

Base: `origin/develop` no merge PR #82, `eb8c0837e3144f8d27429dffc05bb3683169d59a`. A publicação dessa base permanece pendente da confirmação operacional após inventário; o commit documental `c49118d` na branch `codex/gallery-preview-exposure-and-installable-ui` preserva o plano e o estado remoto. Nenhuma operação remota foi feita durante o planejamento das novas changes.

Pontos localizados para implementação: import_photo_source/set_parent_gallery_cover, resolvedores de capa e parent_gallery_details em backend/app/main.py; testes de capa em test_gallery_workflow_remediation.py/test_derived_galleries.py. A prévia admin_preview já é limpa e limitada. CSS compartilhado ainda contém cores literais. Executar testes backend somente com DATABASE_URL apontando banco temporário explícito: as fixtures recriam tabelas.
