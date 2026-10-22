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

## 6. Integração após a publicação de pagamentos em 21/10/2026

- [x] 6.1 Integrar main 21b89c3 na branch existente por merge, preservar guards tardios/recuperação e snapshots imutáveis; incorporar o recibo documental de #265 e comprovar interação recuperação/troca de chave/compra nova e legado, reutilizando regressões e transporte sintético. Evidência: merge local a65e962, matriz PostgreSQL77/0 e recibo documental de #265 incorporado por cherry-pick, sem publicação do cofre.
- [x] 6.2 Corrigir a orientação antiga do card sobre desligar PIX global, conservando opções por link, conferência do recebedor, senha/OTP, segredo transitório e PIX manual. Evidência:13 testes do card aprovados, lint0erros/34avisos e build/TypeScript aprovados após merge main21; nova validação será necessária após integrar o delta de #266.
- [x] 6.4 Integrar localmente o candidato de #266 (mínimo/primeiro clique) mantendo ambos os contratos e repetir as regressões afetadas/backend e suíte/gates frontend do candidato único; preservar o manifesto de release0084 como candidato SEM cofre e comprovar recusa de publicação desta branch com0085, sem ampliar allowlist ou mascarar o gate. Evidência:merge be3f36e;37 testes PostgreSQL/610 frontend aprovados, lint/build/TypeScript/Ruff e OpenSpec134/0, conforme validation.md.
- [x] 6.3 Atualizar revisão e plano com a base publicada e os limites de migration/keyring/rollback, retargetar o mesmo PR #262 para main, revisar diff/segredos e executar gates afetados e CI final do novo head. Não realizar merge do PR, publicação, migration ou provisão real. Evidência:CI782/39699171014 concluído success no head27910b38; próprio PR262 open/draft contra main. A melhoria de apresentação posterior tem gate final próprio na change hide-reopened-purchase-from-active-lists.
- [x] 6.5 Separar no teste técnico de política o snapshot positivo do manifesto e a recusa real de HEAD protegido, mantendo todas as comparações e gates de produção; acrescentar regressões Git reais e sua execução explícita em CI, sem mocks/skip ou aprovação do cofre pelo manifesto0084. Evidência:7 testes Git reais aprovados, política completa aprovada com publication_candidate_ready=false/api_fora_do_escopo; verificador/classificador/manifestos operacionais não alterados por esta correção.
- [x] 6.6 Reproduzir e corrigir somente a fingerprint histórica do indicador público de build apontada pelo gitleaks no CI780, sem reescrever histórico ou ampliar exceções; comprovar a varredura completa e a detecção de canário sintético independente. Evidência:gitleaks8.24.3/checksumoficial;histórico integral do candidato1ocorrência antes/0depois;canário independente continua recusado, exit1; ver validation.md. CI do novo head ainda deve concluir.

## Workflow follow-up

- Revisão humana, integração dos dois PRs, inventário remoto e autorização separada antecedem qualquer publicação/migration/provisão real.
- Cadastro de API Key real será feito pelo proprietário somente na interface publicada e validada.
- Sincronizar specs principais e arquivar somente após revisão humana.
- As tarefas 1–5 e seus resultados são checkpoints anteriores; a aprovação do candidato integrado desta retomada depende de 6.1–6.3. Código de #261 e o fluxo de release API/web que proíbe migrations permanecem fora do escopo.
