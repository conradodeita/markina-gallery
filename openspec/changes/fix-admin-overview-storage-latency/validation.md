# Validação — 30/10/2026

## Base e isolamento do trabalho

`git fetch origin main` confirmou `86c808064906933c9cdc0e5e9b88d32ccceb385c`, igual ao HEAD inicial. Branch nova `codex/fix-admin-overview-storage-latency`. A listagem compacta de chats disponíveis não mostrou outro executor ativo neste subsistema; não houve envio de mensagem, edição de outros worktrees ou deploy concorrente. Registros locais da limpeza de testes (`purge-owner-test-purchases`) permanecem fora desta alteração.

Diagnóstico inicial em `docs/diagnostics/admin-overview-performance-2026-10-30.md`: API no Chrome 16.801ms; helper publicado instrumentado 16.536,10ms. Identificada consulta de tenant por arquivo e resolução repetida de raízes. A skill OpenSpec Apply orienta a change; JEV/memória foram utilizados na etapa de diagnóstico, sempre confrontados com código/runtime atuais.

## Comparação no mesmo acervo — READ ONLY

Processo Python separado dentro do container existente, transação `REPEATABLE READ, READ ONLY`, rollback final e consultas filtradas pelo tenant autorizado. Primeiro executou-se o helper publicado, depois o candidato em memória **somente desse processo**, sem gravar ou substituir nenhum arquivo do servidor/API. As três medições devolveram exatamente **2.804.669.796 bytes**, com resultado disponível.

| Rotina | Duração | SELECTs |
| --- | ---: | ---: |
| Publicada, sem instrumentação detalhada | 16.305,33ms | 17.602 |
| Candidata, primeira leitura | 3.622,49ms | 5 |
| Candidata, cache válido | 1,16ms | 2 |

SHA256 do candidato medido: `51788c000ed2516006abd05de3aa19d0a6a34bc23def1a557c62a4c7724ff714`. Cerca de 78% de redução no tempo frio do helper nesta execução; não é medição do endpoint HTTP candidato nem garantia de latência em todas as condições. A API continua na versão publicada anterior. Os bytes iguais incluem originais, derivados e ajustes atuais/legados presentes no acervo observado.

## Fronteiras de arquivos

Ensaio nativo Linux com diretório temporário e arquivos exclusivamente sintéticos recusou **3/3** tentativas: symlink para fora da raiz, symlink para outro tenant e histórico resolvido em item diferente. Diretório temporário eliminado pelo próprio contexto; nenhuma mídia operacional foi modificada. Esse ensaio complementa a indisponibilidade de symlinks no Windows local.

## Testes locais e revisão

Primeira execução de regressões: 14 aprovados, 2 skips de symlink no Windows, 1 falha na instrumentação do teste de queries. A fixture tinha expirado o objeto Tenant no commit e ler `owner.id` já dentro do trecho medido adicionava um SELECT da própria fixture. O teste foi corrigido para resolver o UUID antes do listener. A comparação real independente acima também confirmou os 5 SELECTs frios e 2 de cache.

Resultados finais, com SQLite exclusivamente sintético fora do repositório:

- `tests/test_tenant_storage_metrics.py`: **13 passed, 2 skipped**, 146,70s. Inclui queries constantes, TTL sem renovação deslizante, invalidação, bancos/raízes/tenants distintos, suspensão inicial/durante coleta, erro sem parcial, originais/derivados/ajustes legados e atuais, deduplicação, capacidade limitada e coalescência sem bloquear outro tenant.
- `tests/test_storage_metrics.py`: **3 passed** na execução inicial, sem falhas nesse arquivo; helper global preservado. Os dois skips acima são limites de symlink verificados separadamente no Linux.
- `tests/test_derived_galleries.py -k admin_validation_summary`: **3 passed**, 47,25s. Contrato agregado/autorização, importações públicas e restritas por estado, indisponibilidade de storage sem ocultar demais métricas.
- `tests/test_tenant_producers.py -k validation_summary`: **1 passed**, 20,29s. Dados de outro tenant e galeria removida não entram nas contagens, jobs ou galerias recentes.
- **Total: 20 casos aprovados, 2 skips explícitos**, mais 3 fronteiras de symlink verificadas nativamente.

Avisos preexistentes: FastAPI `on_event` deprecated e ciclo de FKs em DROP de fixture SQLite. Nenhum corresponde à correção. Não houve instalação/atualização de dependências ou uso dos bancos/containers locais de outros projetos.

Ruff dos cinco arquivos Python novos/alterados e compilação Python passaram. `openspec validate fix-admin-overview-storage-latency --strict` e `git diff --check` passaram. Nenhum helper compartilhado de processamento/entrega foi alterado. A resolução local reaproveita `media_namespace` e preserva os checks de confinamento e prefixo histórico antes/depois da resolução. Revisão proporcional removeu apenas imports, materialização ORM e loops de contagem diretamente substituídos; não foi iniciada refatoração geral.

## Publicação

Implementação e validação local concluídas; sem push, merge, migration ou deploy desta correção até este checkpoint. Nenhum código frontend foi alterado; lint/typecheck/build frontend não são necessários para este delta exclusivamente backend. Validação visual de latência na versão publicada corrigida depende do release autorizado. O candidato foi apenas executado em processo isolado de leitura, não instalado na API. A change permanece ativa; não sincronizar/arquivar automaticamente.
