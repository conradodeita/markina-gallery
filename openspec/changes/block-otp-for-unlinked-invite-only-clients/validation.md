# Evidências e continuidade

## Escopo e ambiente

- Autorização humana: proposta aprovada para implementação na conversa em 2026-10-07.
- Checkout local: `C:/Users/Conrado/Documents/Photo Delivery`, base Git `95dbab718b5f0b705fa127d86649b308dba8ba36`.
- Implementação limitada a `backend/app/auth.py`, `backend/app/main.py`, `backend/app/public_gallery_access.py`, `backend/tests/test_auth.py` e esta change. Alterações locais preexistentes preservadas.
- Não houve deploy, migration, alteração de segredos ou envio de OTP real. Os testes usam fixtures sintéticas e o transporte de teste existente.
- Esta evidência não comprova a versão em homologação nem o recebimento real no WhatsApp. A implementação precisa ser integrada ao baseline de deploy antes de ensaio remoto autorizado.

## Contratos verificados

- Link público `invite_only` sem vínculo ativo: resposta neutra, nenhuma entrega WhatsApp, nenhum vínculo ou sessão criado.
- Vinculação posterior: desafio sem entrega rejeita código de seis dígitos; reenvio autorizado gira o segredo, cria entrega e permite autenticação.
- Convite individual: somente o telefone da identidade destinatária recebe código.
- Vínculo suspenso e capacidade expirada/revogada: reenvio mantém resposta neutra e não cria outra entrega.
- `standard`, `collective_protected` e entrada sem contexto preservam os fluxos existentes; cadastro e vínculo continuam dependendo da comprovação OTP.
- Links privados compartilhados preservam a associação autorizada por sua própria spec, inclusive para outra cliente; convites individuais privados preservam a identidade destinatária.
- Privadas habilitadas em origem `deleted` preservam solicitação, reenvio e autenticação sem reabrir a origem pública.

## Resultados

- Antes da revisão de compatibilidade, `python -m pytest -q tests/test_auth.py`: 20 testes aprovados; `test_gallery_lifecycle.py` nos cenários de modos de acesso/convite privado: 3 aprovados.
- Após corrigir a preservação dos links compartilhados e da origem excluída, `python -m pytest -q tests/test_auth.py -k 'private_context or invite_only'`: 7 aprovados, 17 deselecionados, 64,65 s.
- `python -m ruff check app/auth.py app/main.py app/public_gallery_access.py tests/test_auth.py`: aprovado.
- `npx --yes @fission-ai/openspec validate block-otp-for-unlinked-invite-only-clients --strict`: aprovado com OpenSpec 1.14.1.
- `git diff --check` nos quatro arquivos backend alterados: aprovado; apenas avisos de conversão LF/CRLF.
- Validação integrada final sobre o código revisto em 2026-10-07: `python -m pytest -q tests/test_auth.py tests/test_gallery_lifecycle.py -k 'not test_gallery_lifecycle or test_public_access_modes_require_session_and_backend_authority or private_invite'`: 27 aprovados (24 autenticação + 3 acesso/convite privado), 52 deselecionados, em 239,39 s. Somente dois avisos preexistentes de depreciação do `on_event` FastAPI.

## Revisão de compatibilidade

A inspeção dos testes existentes mostrou que alguns injetam diretamente um hash de OTP e validam a resposta HTTP, sem conferir a entrega na outbox. Isso podia esconder bloqueio do envio para privadas compartilhadas. A regressão adicionada exige duas entregas (primeira solicitação e reenvio) antes de validar o login, nos quatro pares de escopo privado e estado da origem. O desenho e os cenários desta change foram reconciliados com `consolidate-shared-private-galleries-and-progressive-sales`.

## Próximo passo operacional

Após revisão humana, integrar somente os arquivos desta change, executar CI no baseline de integração e apresentar inventário/plano de impacto zero para autorização específica de deploy. Sincronização da spec principal e arquivamento dependem de revisão humana; não foram realizados.

## Integração atual em 2026-10-07

As seções anteriores registram o primeiro checkout e são históricas. A integração para PR usa `origin/develop` em `25d362539f952591baff796bf756439dd9839966`, branch `codex/block-unlinked-invite-only-otp`, em worktree gerenciado separado. O diretório primário e seus arquivos não relacionados foram preservados.

Escopo atual: três arquivos da aplicação backend, novo `backend/tests/test_invite_only_otp.py` e esta change. Nenhuma mudança de frontend, migration, canal, segredo real ou recurso remoto. Os testes novos usam duas contas sintéticas com o mesmo telefone, fixture existente de isolamento e bancos SQLite temporários com FKs habilitadas. A regressão legada usa banco temporário próprio, sem acessar dados de homologação.

A adaptação conserva a validação de contexto multitenant e a reautenticação por galeria da versão atual. Respostas de contexto válido inelegível continuam neutras; capacidade inválida continua rejeitada pelo contrato existente. Identidade e vínculo de A não autorizam entrega em B. O segredo suprimido é escolhido antes de persistir o desafio, evitando até a persistência transitória de um OTP verificável não entregue.

Durante validação, três expectativas de entrega pendente encontraram o caminho sandbox aceito sem chave criptográfica. A fixture de regressão agora fornece chave sintética de teste e exige outbox em queued com payload criptografado antes de revogar o vínculo, sem mockar efeitos internos. Isso permite verificar a expiração e eliminação do payload no reenvio suprimido.

Ruff completo backend passou; OpenSpec 1.14.0 estrito aprovou 80 itens, zero falhas. A suíte backend completa, frontend e scan de segredos serão executados pelo CI do PR; estes resultados locais não comprovam deploy nem entrega real de WhatsApp. Resultados finais dos testes focados serão registrados antes do commit.

- Regressões legadas sobre SQLite descartável próprio: `python -m pytest -q tests/test_auth.py tests/test_gallery_lifecycle.py -k 'not test_gallery_lifecycle or test_public_access_modes_require_session_and_backend_authority or private_invite' --tb=short`: **18 passaram, 59 deselecionados, 273,37 s**. Dois avisos de on_event e 17 avisos de ciclos de FK no drop_all das fixtures antigas; sem falha.
- Regressões de entrega pendente após corrigir a fixture criptográfica: `python -m pytest -q tests/test_invite_only_otp.py -k reenvio_sem_vinculo --tb=short`: **3 passaram, 14 deselecionados, 47,50 s**.

- A primeira execução conjunta de test_invite_only_otp.py e test_tenant_client_auth.py terminou com 41 aprovados e as três falhas já delimitadas da fixture sandbox antiga, em 519,18 s. Os **27 casos existentes de test_tenant_client_auth.py passaram**; a aplicação não foi alterada após esta execução ser iniciada. Somente os três testes novos foram ajustados para representar entrega realmente pendente.
- Validação final do arquivo novo completo após esse ajuste: `python -m pytest -q tests/test_invite_only_otp.py --tb=short`: **17 passaram, 208,94 s**, apenas dois avisos preexistentes on_event.
- Total de casos distintos validados no baseline atual: **62** (17 novos + 27 multitenant existentes + 18 regressões legadas). A cobertura existente foi reutilizada porque a única alteração posterior era a fixture dos três casos novos, todos reexecutados e aprovados. Docker local indisponível; PostgreSQL e a suíte integral ficam no CI. Nenhuma alteração de infraestrutura foi tentada.
- Revisão final do diff: apenas elegibilidade antes de OTP, sua integração em solicitação/reenvio e testes/artefatos relacionados. Validação final não inclui frontend local porque nenhum arquivo frontend foi alterado; lint/testes/build frontend permanecem no CI obrigatório.

## Entrega para revisão

- Commit de implementação: `9d182e446dc161365c3bded423e85d5925dd0140`.
- PR **#144**, base develop: https://github.com/conradodeita/markina-gallery/pull/144 . Criada e anexada ao chat.
- Primeiro CI iniciado: run `37719121217`, com backend/frontend/OpenSpec/gitleaks em execução no momento do registro. A atualização documental posterior mantém todos os arquivos de aplicação/testes inalterados; exige validar o CI do HEAD mais recente antes do merge.
- Todas as tarefas locais desta integração foram concluídas. CI verde, revisão humana, inventário/autorização operacional de deploy e ensaio remoto continuam pendentes. Merge não executado; nenhuma publicação remota ou alteração de dados de homologação.
- Próximo executor: consultar checks da PR #144 no HEAD atual. Se falhar, investigar os logs e corrigir somente dentro desta change. Se passar, apresentar inventário/plano e obter autorização de merge/deploy porque a integração em develop publica automaticamente. Manter canais, dados e infraestrutura de terceiros intactos.
