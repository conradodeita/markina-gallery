# Validação

## Resultado local — 12/11/2026

- `frontend`: `vitest run app/admin/settings/whatsapp-panel.test.tsx` — 13 testes aprovados, incluindo primeiro provisionamento, atualização de número existente, erro HTTP e resposta 200 sem instância confirmada.
- `frontend`: ESLint nos dois arquivos do painel — aprovado; `tsc --noEmit` — aprovado; `next build` — aprovado, com 27 páginas estáticas/dinâmicas geradas.
- `backend`: `pytest -q tests/test_admin_security.py` — 27 testes aprovados, 32 avisos de depreciação/ordenação de `drop_all` já ligados ao harness FastAPI/SQLite. Os dois novos testes cobrem gate de signup ativo e repetição idempotente. A fixture usou arquivo SQLite novo em `%TEMP%`, removido ao terminar.
- O teste da rota substituiu `ensure_instance` e fez `_request_json` falhar imediatamente se fosse chamado; portanto não houve rede para Evolution. As respostas foram confirmadas sem telefone integral nem chave sintética.
- `ruff check tests/test_admin_security.py` — aprovado.
- `openspec validate wire-photographer-whatsapp-autoprovision-ui --strict` — aprovado.
- `git diff --check` dos arquivos rastreados — sem erro de whitespace; Git emitiu somente aviso LF/CRLF para o arquivo de teste legado. Verificação separada dos artefatos OpenSpec não encontrou whitespace final.

## Limites e revisão

- Nenhuma migration ou alteração do backend runtime foi necessária: a rota já existente atende à regra e a tela agora a consome no primeiro uso.
- A rota genérica do Next reescreve `/api/:path*` para o backend, então o novo caminho `/api/admin/whatsapp/channel/provision` segue o mesmo proxy das demais chamadas administrativas.
- A edição continua no `PATCH`; o fluxo inicial usa `POST` apenas quando o estado retornado indica provider indisponível. Uma resposta inesperada mantém o número digitado e o pareamento bloqueado.
- Não foi feita chamada real à Evolution, execução em browser autenticado, staging, commit, push, deploy ou operação em produção. A validação cobre o contrato sintético local, não prova o pareamento real.
- Revisão proporcional de refatoração: o fluxo `PATCH` continua necessário para canais provisionados/legados e não foi removido; não há código substituído elegível para remoção nesta change.

## Revisão de binding e prova PostgreSQL — 15/11/2026

- Revisados diffs e consumidores de `whatsapp_binding.py`, `whatsapp_channel.py` e implementação de `whatsapp_tenant_credentials.py`: tenant ativo, segredo cifrado por ambiente/tenant/credencial, recusa de alias coexistente e colisão de identidade, seleção exclusiva por instância/segredo no webhook, upsert do estado do canal e revalidação do provider. A permissão de sandbox do demo continua restrita a development/test; não habilita produção.
- `test_tenant_notification_transport.py` + `test_notification_channel_readiness.py` no PostgreSQL 17.11 descartável 15470: **35 passed**, sem skips/falhas, seis avisos FastAPI preexistentes, 544,33 s. Inclui corrida real de criação do estado, idempotência de credenciais, isolamento A/B, webhook, suspensão/revogação e prontidão por identidade viva, com transportes sintéticos.
- JUnit externo `C:/codex-data/local-review/prepush-whatsapp-bindings-20261115.xml`. Ruff focal passou. Nenhuma instância Evolution real foi criada/pareada e nenhuma mensagem externa foi enviada. A verificação local não comprova a conectividade operacional do provider em produção.

## Revisão semântica documental pré-push — 16/11/2026

- Proposal, design, spec delta, tasks e validation foram comparados com a tela, a rota de provisionamento, o armazenamento cifrado por tenant/ambiente e os testes sintéticos registrados.
- Corrigida na spec delta a descrição de persistência: o segredo do webhook é armazenado cifrado no registro de credenciais; QR e código de pareamento permanecem temporários e não são persistidos. Isso alinha o requisito à implementação e à spec principal.
- A revisão cobre contrato documentado e evidência local existente; não afirma pareamento ou conectividade real com Evolution. O gate operacional do provider continua sem validação externa.
