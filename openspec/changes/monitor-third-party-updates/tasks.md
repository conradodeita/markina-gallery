# Tasks

- [x] 1. Reconciliar inventário de 43 itens contra `d06dcc7460b69188833a79e39a7b05fa694410ea`; incluir Gemma, runtime e componentes identificados; registrar evidência datada e runtime atual não confirmado. Conferido no código e nos registros versionados: worker/health/assets não demonstram inferência; engine SFace, zero jobs/vetores Gemma em 11/10/2026.
- [x] 2. Implementar a política OpenSpec e incorporá-la ao `AGENTS.md`, preservando instruções de segurança, privacidade, revisão e rollback.
- [x] 3. Configurar Dependabot agrupado/semanal para npm, pip, Docker e Actions, com limite de PR e sem automerge. Dependências de runtime Gemma podem receber PR revisável; pesos/modelo e motores especializados não recebem atualização automática.
- [x] 4. Implementar resumo semanal somente-leitura no GitHub Actions, com origem/horário, risco/prioridade, lista vazia distinta de falha/permissão e sem PRs/issues/notificações.
- [x] 5. Criar testes de pins/revisões, tags/digests, candidatos, estado de API, paginação, falhas e proteção contra mutação/deploy/automerge.
- [x] 6. Validar OpenSpec estrito, testes direcionados, CI do PR e revisar branch/diff final. OpenSpec estrito, 9 testes direcionados e revisão manual do diff passaram; os seis checks obrigatórios do PR passaram no SHA `f413d98507f1aa30bdedb169f93ebe90662afb73`. A integração do Code Review não estava conectada. Proteção vigente exige os seis checks e nenhuma aprovação humana; validar novamente no SHA com este registro antes do merge.
