# Tasks

## 1. Contrato e isolamento do trabalho

- [x] 1.1 Verificar PR #260 e criar worktree/branch próprios; validar proposal, deltas, design e dependência em OpenSpec strict, sem alterar o PR pai. Evidência: PR pai draft/aberto em `0959c64`; branch `codex/infinitepay-tenant-credentials`, worktree próprio e strict válido.

## 2. Cofre dedicado e schema

- [x] 2.1 Implementar envelope AEAD/keyring separado, erros neutros e recifragem; testar round-trip, tenant/ambiente/versão adulterados, chave ausente/errada e rotação/restore sintéticos. Evidência: `test_integration_secrets.py` — 15 passed; Ruff aprovado.
- [x] 2.2 Acrescentar tabela dedicada e referências compostas na configuração/compra; migration PostgreSQL aditiva, preservação do legado, bloqueio de FK estrangeira e downgrade destrutivo; atualizar ownership e procedimento de backup/recuperação. Evidência: 2 testes PostgreSQL passaram; `ownership.md`/`operations.md`, cleanup preserva cofre; Ruff aprovado. Gerador global bloqueado por modelo RAW preexistente, registrado em `validation.md`.

## 3. Gestão autenticada e checkout

- [x] 3.1 Integrar cadastro/substituição/desconexão aos desafios existentes, segredo write-only e auditoria mínima; comprovar A/B, autenticação, permissão, CSRF, IDOR, concorrência de versão, chave mestra ausente e ausência de vazamento em chamadas HTTP reais ao backend de teste. Evidência: 6 testes HTTP/ASGI em PostgreSQL + 15 regressões existentes de configuração passaram; nenhuma autorização mockada; Ruff aprovado.
- [x] 3.2 Resolver snapshot de credencial no checkout/retorno, preservar binding legado e bloquear fallback/desconexão insegura; testar A/B, substituição concorrente, transações pendentes, idempotência e PIX independente. Evidência: 5 testes de checkout PostgreSQL + 6 de gestão e 1 callback HTTP A/B passaram; snapshot antigo usado em `/links` e `/payment_check`, concorrência usa um par íntegro handle/credencial, PIX preservado.

## 4. Card existente

- [x] 4.1 Completar somente o card InfinitePay com campo oculto transitório, status fiel, alteração/desconexão e prevenção de abandono; testar envio único, segredo ausente da resposta/armazenamento/navegação, carregamento/erro/sucesso, TypeScript, lint e build. Evidência: 11 testes do card, suíte frontend 63 arquivos/566 testes, TypeScript e build aprovados; lint sem erro (34 avisos preexistentes fora do card).
- Reforço de compatibilidade 4.1: coleta de segredo exige capacidade explícita da API; teste falhou antes e passou após correção. Validação final: 12 testes do card, suíte 63 arquivos/567 testes, TypeScript/lint/build aprovados. Falha temporal fora do diff na execução com build concorrente delimitada e não reproduzida isoladamente nem na repetição integral, conforme `validation.md`.

## 5. Integração e entrega

- [x] 5.1 Executar regressões financeiras e tenant pertinentes, gates de ownership, Ruff, OpenSpec strict e diff/segredos; revisar área alterada por duplicação/código obsoleto e registrar evidências proporcionais. Correções de catálogo/fixture/reset e ARM64 nativo no commit `8465c57d265ed8add463ebf9841b20285fcff4fc`; CI integral [39545805272](https://github.com/conradodeita/markina-gallery/actions/runs/39545805272) aprovado: backend 1751 passed/24 skipped, frontend 567, concorrências PostgreSQL 4+1, cofre PostgreSQL 16 e inventário 1. Imagens nativas AMD64/ARM64, Gemma, gitleaks, OpenSpec (131 itens) e política agregadora aprovados. Revisão em `review.md`; limitação preexistente do gerador RAW permanece delimitada, sem bypass de gates.
- Evidência adicional 5.1: comparações históricas 0075/0070 também reproduzidas e ajustadas ao seu contrato; 23 testes PostgreSQL desses arquivos passaram. Cleanup com credencial gerida preserva ciphertext e permite descriptografia (1 caso reforçado passou). Alterações restritas a fixtures/expectativas e classificações da nova tabela, sem reescrever histórico de migrations.
- [x] 5.2 Preparar runbook de migration/master key/rotação, release API/web coordenado e rollback compatível com ciphertext e compras; criar PR draft próprio dependente do #260, acompanhar CI final e registrar SHA/resultados e GO/NO-GO. PR #262 revisável com CI integral verde em `8465c57`; plano em `release-plan.md`, operação do cofre em `operations.md`, revisão em `review.md`. GO somente para solicitar revisão/autorização de integração; publicação operacional NO-GO até os gates humanos e migration separada do plano. Registro documental de encerramento não altera código, runtime ou credenciais; resultado exato do head documental será conferido e anexado ao PR antes da entrega.

## Workflow follow-up

- Revisão humana, integração dos dois PRs, inventário remoto e autorização separada antecedem qualquer publicação/migration/provisão real.
- Cadastro de API Key real será feito pelo proprietário somente na interface publicada e validada.
- Sincronizar specs principais e arquivar somente após revisão humana.
