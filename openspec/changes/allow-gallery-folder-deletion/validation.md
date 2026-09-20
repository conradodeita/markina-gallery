# Validação e continuidade — 2026-09-20

- Backend: `pytest backend/tests/test_derived_galleries.py -k "delete_content_folder or delete_empty_folder or folder_deletion or operational_folder_photos or photo_deletion or photo_bulk_deletion" -q -x`: **11 passed**, 153,18s. Banco SQLite sintético isolado na worktree; nenhum dado real acessado. Verificados rollback integral, arquivo operacional removido só após sucesso, histórico confirmado com prévia e entrega preservados, escopo privado após exclusão da origem, autenticação, pasta técnica e regressão avulsa/lote.
- Frontend: `vitest run app/admin/galleries/gallery-editor.test.tsx app/admin/galleries/galleries.test.tsx`: **62 passed**, 27,87s. Confirmação/cancelamento, bloqueio comercial visível e atualização das duas interfaces.
- `tsc --noEmit`, build Next e Ruff passaram. ESLint: zero erros, oito avisos preexistentes (img e parâmetros sem uso). OpenSpec strict e `git diff --check` passaram.
- Correções de teste durante execução: APP_ENV precisa ser development para cookies HTTP do TestClient; fixture MediaJob usa queued; testes da pasta agora distinguem explicitamente Abrir/Excluir.
- A alteração parte de origin/develop 9b83f062, em worktree própria. A PR facial #88 permanece independente. Ao integrar ambas, preservar a limpeza PhotoAnalysis introduzida pela change facial.
- Pendente 3.2: revisão humana e teste autenticado em homologação após CI e deploy autorizado. Não houve deploy, migration nem exclusão de pasta real. A sincronização/arquivo exige revisão humana conforme AGENTS.md.

Revisão final fortaleceu o teste de bloqueio com pedidos e PaymentCommunication reais (sem mock), confirmou rollback do cancelamento de outra compra, usou lifecycle_status=deleted persistido na origem privada e incluiu pastas vazias em ambos os estados. Suíte completa frontend conjunta: 307 aprovados.
