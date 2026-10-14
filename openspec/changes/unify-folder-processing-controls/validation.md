# Evidências e continuidade

- O proprietário aprovou o escopo em 13/10/2026 com “Prossiga” e reforçou isolamento por fotógrafo e integração com o Monitor do sistema.
- Base correta: `4fe9b6885f78a662b3888593b4cd2278b964efa3`, branch `feature/unify-folder-processing-controls`, worktree já anexado `C:/codex-data/worktrees/raw-development-tenant-port/Photo Delivery`. Ele estava limpo antes desta change. O checkout principal está defasado e contém trabalho local de outras changes, que será preservado.
- A primeira investigação ocorreu no checkout defasado; uma regressão capturou uma prévia desaparecendo enquanto a consulta periódica aguardava resposta. Os testes e a migration produzidos nessa investigação não são o pacote final e seus resultados não validam a base integrada.
- Na base integrada, o armazenamento e a autorização por pasta/fotógrafo já existem. Não é necessária a migration que o primeiro planejamento supunha. A revisão dos artefatos mantém o comportamento aprovado e reutiliza o contrato vigente.
- Causa delimitada a confirmar na base atual: polling chama `inspectFolder`, que limpa `photos` antes de receber a consulta; o contador fica no conteúdo condicional da pasta e não contém sua identidade. Uma falha de atualização também podia substituir o editor inteiro.
- Arquivos anteriores às edições foram preservados em `.codex-tmp/unify-folder-baseline/`, somente como referência local para revisão.
- Nenhum commit, push, deploy, migração remota, sincronização de specs principais ou arquivamento foi executado nesta change.

## Checkpoints locais

- Regressão backend: antes da correção, mudar parâmetros públicos deixava o job `cancelled`, geração 1, em vez de `queued`, geração 2. A correção reutiliza `configure_folder`/`enqueue` existentes e mantém a dependência facial privada.
- `python -m pytest tests/test_folder_processing_api.py tests/test_folder_processing.py tests/test_system_monitor.py -q --disable-warnings`: 49 aprovados no checkpoint anterior à inclusão da listagem administrativa de restritas. Inclui acesso alheio recusado, fila alheia intacta, consultas sem trabalho e uma execução real contada como `work.preview_adjustment`. A validação afetada pela listagem será repetida.
- Regressões UI na base integrada, antes da correção: 2 falhas; prévia desaparecia durante consulta pendente e lote não possuía indicador acessível identificado pela pasta. Logs locais `.codex-tmp/ui-red.log`. Após correção: 2 aprovados (`ui-green.log`).
- O typecheck foi repetido depois dos testes adicionais; ver resultado final abaixo.

- Checkpoint frontend após integração: 78 testes direcionados aprovados (painel, editor, upload e cliente facial). Inclui defaults públicos/privados, autosave serializado, troca com gravação pendente, falha/retentativa, comparação ampliada, lote persistente com 50/100 bytes e uma lista de dez pastas privadas com um painel.
- Suíte frontend ampla: 501 aprovados e uma expectativa obsoleta do botão manual no card de cliente. Teste atualizado para verificar o link ao painel único; repetição final pendente.
- Checkout defasado: 22 arquivos restaurados byte a byte ao baseline anterior a esta task e 12 rascunhos novos retirados após preservação em `.codex-tmp/unify-folder-draft-restored-20261013/`. Mudanças preexistentes preservadas.

- Build de produção Next.js aprovado (`.codex-tmp/build.log`), typecheck aprovado, lint sem erros (32 avisos nesse checkpoint, em maioria preexistentes) e OpenSpec estrito aprovado.
- Uma execução ampla frontend teve timeout de 5 s em um teste de notificações fora do escopo; isoladamente, esse arquivo passou 5/5. A execução completa final com `--maxWorkers=2` passou 503/503 sem alterar timeout ou contrato do teste.
- A regressão ampla backend identificou a expectativa antiga de `enqueue=True` após `configure_folder` no teste de fonte limpa. O novo contrato já enfileira automaticamente; o teste agora exige que a admissão manual adicional seja idempotente (`False`), mantendo os mesmos três renders e comparações de pixels. O ensaio de workers A/B preserva a mesma expectativa atualizada, com parâmetros/marca/paths próprios e fila B intacta.

## Resultado final das regressões

- Backend amplo: 189 aprovados, 1 falha na expectativa antiga de enqueue manual e 1 ignorado em 607,17 s. Código de produção permaneceu igual após esse checkpoint; a falha foi corrigida somente no teste, conforme autosave especificado.
- Complemento backend: 18 aprovados e 1 ignorado em 96,74 s, incluindo a regressão de fonte limpa antes falha, workers A/B, configuração e filas por fotógrafo. Resultado combinado: 207 testes aprovados sem falhas pendentes.
- Limites PostgreSQL: `test_folder_processing_migration` requer PostgreSQL descartável não configurado; a corrida de suspensão durante render em `test_tenant_media_jobs` também exige PostgreSQL. Ambos foram ignorados, sem declarar execução. Esta change não cria migration nem altera o protocolo de claim/publicação; seus testes existentes continuam disponíveis para esse ambiente.
- Frontend completo com concorrência reduzida: **60 arquivos, 503 testes aprovados**, em 155,71 s (`npm test -- --maxWorkers=2`). O limite foi passado somente ao comando; nenhum timeout ou configuração do produto foi alterado.
- Após remover o último prop sem chamador do painel retirado dos cards de cliente, repetição dos dois arquivos afetados: 11 aprovados em 7,98 s.
- Typecheck final aprovado; ESLint final: 0 erros e 31 avisos preexistentes nos arquivos preservados. Ruff dos seis arquivos Python alterados aprovado. `git diff --check` sem erros. OpenSpec estrito aprovado.

## Revisão e higiene

- Diff revisado contra `4fe9b68`: backend limitado a autosave público, geração/progresso da API por pasta, opção administrativa de listar restritas e regressões correspondentes. Workers, motores, quotas, dados biométricos, permissões do Monitor e migrations não foram modificados.
- Removidos os painéis globais facial/prévia, seus testes exclusivos/CSS e o cliente administrativo facial sem chamadores. O cliente facial público e os controles globais operacionais permanecem. O painel contextual mantém comparação protegida/ampliação e retentativa facial por pasta. Cards de clientes mantêm seus controles comerciais/acervo e levam a Imagens para processamento.
- Editor mantém JPEG/RAW, capas, seleção/exclusão de fotos, progresso em bytes, backpressure e gates existentes; contadores são indexados por destino e consultas de atualização preservam a estrutura. A listagem percorre páginas para permitir selecionar restritas após o primeiro limite.
- Nenhuma validação estética de fotos reais, benchmark de throughput Gemma/Lightcraft ou validação visual autenticada no servidor foi executada. Aceitação do fotógrafo ocorrerá após publicação autorizada; esses limites não são apresentados como testes locais aprovados.
- Mudanças anteriores no checkout principal foram preservadas; rascunhos desta task permanecem somente em referência local ignorada. A implementação ativa está no worktree integrado e na branch `feature/unify-folder-processing-controls`.

- Build de produção final, já com listagem paginada e painel higienizado: aprovado (`.codex-tmp/build-release.log`). Todas as nove tasks locais foram reconciliadas; publicação e revisão humana de specs/arquivamento não fazem parte desta execução.
