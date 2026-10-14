# Validação — 14/10/2026

## Diagnóstico remoto somente de leitura

- Checkout e código do container iguais: commit `3b15529c4bd5fd68fdf2d22f91a869c0b5d3bad2`; SHA256 conferidos para engine e search_worker.
- Galeria real: duas pastas de conteúdo, 2.691 fotos; banco tem 3 pastas/2.693 ativos incluindo objetos técnicos de capa. Owner único, cliente único. Schema `20261014_0080`.
- Índice SFace: 10.531 rostos em 2.687 fotos; 2.691 jobs de índice concluídos, sem pendência de indexação. Quatro fotos sem rosto são resultado válido.
- Consulta original: 2.691/2.691 snapshot pronto, compare_done=0; failed após 376,77 s e quatro claims, last_error_category=timeout.
- Busca acompanhada no navegador: 0% e 2.691 itens restantes, estado searching na segunda tentativa após 159,57 s; terminou em failed. Logs mostram FacialJobError por lease expirado durante callback.
- Worker de busca: 512 MiB, 0,75 CPU, nove reinícios na última inspeção; contador cgroup memory.failcnt=0. Não afirmar OOM: evidência observada sustenta lease vencido e recarga integral redundante.

## Ambiente e comandos locais

Worktree isolada baseada na versão implantada; Python 3.12, Windows, SQLite e NumPy. Nenhum banco/arquivo real foi usado nos testes.

- Regressão inicial: `python -m pytest tests/test_facial_search_latency.py -q` falhou antes da correção, observando 99 leituras de snapshot em oito fotos. A seleção foi refinada para distinguir leituras pontuais de entidades expiradas; o código anterior ainda executa duas leituras integrais por rosto.
- `python -m pytest tests/test_facial_search_latency.py tests/test_facial_engine.py tests/test_face_region_search.py -q`: 25 aprovados na etapa de paginação; somente avisos preexistentes de on_event.
- `python -m pytest tests/test_facial_search_worker.py tests/test_tenant_facial_maintenance.py tests/test_facial_search.py tests/test_facial_integration.py tests/test_facial_jobs.py -q`: 57 aprovados antes da condensação da autorização; contratos não alterados dessas áreas conservam validade, os caminhos alterados foram repetidos nas suítes abaixo.
- `python -m pytest tests/test_facial_search_latency.py tests/test_facial_engine.py tests/test_tenant_facial_maintenance.py -q -s`: 30 aprovados com guard do engine condensado; avisos preexistentes de on_event.
- `python -m pytest tests/test_facial_search_worker.py tests/test_face_region_search.py tests/test_facial_search_latency.py -q -s`: 38 aprovados com autorização do worker condensada, 340,19 s com processos de teste concorrentes na máquina.
- `python -m pytest tests/test_facial_search_latency.py -q -s`: 12 aprovados em 157,54 s, incluindo cancelamento durante descriptografia, perda/retomada de lease, bloqueio de publicação após invalidar índice, progresso com comparação simulada de 320 s, paginação atravessando fotos e volume equivalente.
- `python -m pytest tests/test_facial_search_latency.py -k condensed_request_guard tests/test_facial_calibration.py tests/test_facial_rollout.py -q`: nove negativos aprovados, 22 deselected; este comando NÃO executou os testes de calibração/rollout.
- `python -m ruff check backend/app/facial/engine.py backend/app/facial/search_worker.py backend/tests/test_facial_search_latency.py`: aprovado.
- `git diff --check`: aprovado; diff restrito aos dois módulos, novo teste e change.
- `npx -y @fission-ai/openspec@latest validate fix-facial-search-latency --type change --strict --no-interactive`: válida.

## Evidência de volume e progresso

- Fixture: 2.691 fotos sintéticas e 10.531 envelopes de 128 dimensões, sem detector/modelo real.
- 83 leituras de até 128 rostos mais EOF; todas as fotos retornam uma única candidata, ordenadas conforme contrato; progresso exatamente 1..2.691, mesmo com fotos atravessando páginas; menos de 20 entidades ORM permanecem na sessão.
- Comparação isolada: 57,42 s antes de condensar consultas redundantes; 7,14–7,94 s depois. Essa medição não inclui callback completo de autorização do worker, HTTP, fila nem hardware Oracle; não prometer esse prazo ao cliente.
- Comparação simulada atravessou lease inicial de 120 s e terminou em uma tentativa após 320 s, com renovações e contadores reais por foto.
- Negativos preservam recusa para cliente bloqueada, registro expirado, modo coletivo legado, galeria desativada, política suspensa e mudanças de modelo, qualidade, geração ou aviso.

## Limitações

Não foi executado build Docker ARM nesta etapa local. Importação no runtime real, saúde, recursos e consulta autenticada ainda dependem da aprovação operacional e da task 3.3. Não medir precisão/recall nem alterar modelo, threshold, gates ou dados. Totais das suítes se sobrepõem; não somar como testes únicos. Frontend não foi alterado e seus lint/typecheck/build não são necessários para este diff.
