# Validação — erro no retorno do Google Picker

> **EVIDÊNCIA HISTÓRICA — NÃO RETOMAR.** O fluxo Google Picker foi aposentado em 25/11/2026; este registro não é instrução de correção ou provisionamento.

Data: 20/11/2026

## Sintoma e limite da evidência

O proprietário informou que o diálogo do Google Picker fecha após clicar em `Selecionar`, mas a página não muda e não apresenta a pasta selecionada nem `Autorizar esta pasta`. O navegador não esteve acessível ao executor e o callback real não foi capturado. `Action.ERROR` é uma hipótese plausível, não uma causa confirmada.

## Regressão e correção

- O teste sintético do callback `ERROR` falhava antes da alteração: não havia mensagem visível.
- A correção reconhece `Action.ERROR`, fecha o diálogo e apresenta somente uma mensagem genérica. Não cria candidata, não envia `/picker/authorize` e não exibe o detalhe de erro nem o ID sintético da pasta.
- Validação focada em 20/11: Vitest `google-drive-folder-picker.test.tsx` passou com 3/3 testes; ESLint nos dois arquivos alterados passou; `openspec validate enable-platform-backup-runtime --type change --strict` passou; `git diff --check` passou.
- O manifesto de release API/web foi atualizado para fixar o blob exato revisado do seletor (`115e2cc9d7c6ed2ff78ce61acd41cb268edd46ca`, conferido por `git hash-object`); essa reconciliação é necessária para o gate de candidatura e não executa publicação.

## Limitações locais e CI integrado

- `npx tsc --noEmit` no worktree reportou erros em tipos gerados em `.next/types` para exports de `calculateWatermarkPreviewFontSize` em `app/admin/settings/page.tsx` e `Trend` em `app/admin/system-monitor/page.tsx`. Esses arquivos não foram alterados. A limitação foi superada para integração pela CI limpa, que executou lint, Vitest e build no SHA revisado.
- O build local não foi concluído porque `frontend/node_modules` é um junction para dependências em outro worktree: o Turbopack rejeitou a resolução fora da raiz e a tentativa com webpack não resolveu pacotes de fontes. A CI executou `npm ci` no candidato e `npm run build` com sucesso.
- A primeira CI do commit `727ecbb1` passou frontend (lint, suíte e build), OpenSpec, Gitleaks e builds das imagens frontend AMD64/ARM64, mas falhou no gate `homolog-inventory-policy` porque o manifesto ainda pinava o blob anterior do seletor. Após reconciliar o pin, a CI `44764183082` do commit `64657ee6a5f81de4c1cec621870644c26f35a18c` concluiu success: frontend (lint, Vitest, build), builds AMD64/ARM64, OpenSpec, Gitleaks, `ci-scope`, `homolog-inventory-policy` e `gemma-runtime` passaram. Jobs de preflight e publicação ficaram ignorados por ser evento de PR; nenhuma publicação ocorreu.
- Após reconciliar o pin, `python scripts/test_production_release_workflow_policy.py` passou (`publication_candidate_ready=true / somente_api_web`) e `python scripts/test_prod_app_release_scope.py` passou com 28 testes. No Windows, os testes desta última suíte exigem `GIT_CONFIG_COUNT=0` no processo local porque o ambiente do Codex injeta configuração Git com um valor vazio; o runner Linux não apresenta essa particularidade.
- PR #395 passou na CI `44765073071` no SHA revisado `bf8f3e82ebea58be7a5cdec0837679dae9f94472`. O merge squash `ebfed53203e5468f96558546b58b14e44b9d59c4` tem a mesma árvore Git da revisão.
- A primeira CI da `main`, `44766249636` tentativa 1, falhou somente no preflight porque `origin/main` local do host ainda apontava para `bf546503`; a recusa ocorreu antes de produzir inventário/runtime, sem publicação. A instalação protegida `44770174794` avançou somente `origin/main`, instalou a ponte e o wrapper root-only revisados com backups preservados e comprovou `containers_unchanged=true`.
- A tentativa 2 da CI `44766249636` concluiu `success`. Preflight `136407269255` confirmou a base aprovada: API `sha256:a18a802c926ea5689b4be0c873f0eca3e929b826f609b6a92a8445eb9d02ff38`, web `sha256:87aa7a92d4e22805ad341c957c6061827830c41a6598bb1f3be5c9b5ad9b27ba`, schema `20261113_0126`, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, Nginx `127.0.0.1:8080` e healthchecks HTTPS 200. Fingerprint de inventário: `f41cda6d04c6b82e812197753742d2a04e6d40129b22095b3b5fd847610c15b0`.
- O artifact ARM64 foi validado no mesmo SHA, sobre a imagem-base API aprovada (`sha256:a18a802c926ea5689b4be0c873f0eca3e929b826f609b6a92a8445eb9d02ff38`), bundle SHA-256 `a62be20cf15d33d6c405d935b350d93ec2461c00f68a7ad1db77e69c27a7a73c`. O handoff `136409130168` emitiu fingerprint `b1bda616950cda78fc90cf6497de263cc04f5c66e17f8dbd4d9d91808fbcc922`.
- A publicação protegida `production-app-release` do run `44766249636` concluiu `success`: API `sha256:6542cb04aa28b065f072430a2530deeb60005c42522a643d03b15b9d1de7302f` e web `sha256:ed4ed1329b3843bb1b1f63de958bf9d68db20e28f1b513ac460c30c9d7d64eb3` saudáveis; `APP_ENV=production`, processamento facial ativo e Nginx recarregado. Os endpoints públicos `/healthz`, `/api/health` e `/` responderam HTTP 200 após a publicação. O SHA ativo é `ebfed53203e5468f96558546b58b14e44b9d59c4`.
- O proprietário repetiu o teste após o release: senha/TOTP habilitam o botão, o Picker abre, mas fecha após `Selecionar` sem apresentar candidata ou erro. Portanto #395 não resolveu o sintoma real; `Action.ERROR` não foi confirmado. A reprodução integrada subsequente está em [validation-picker-focus.md](validation-picker-focus.md).

## Estado operacional após publicação

O release publicou somente API e web, sem migration, backup real, instalação/ativação do timer ou alteração do vínculo protegido. A confirmação funcional da seleção e o ensaio sintético no Drive permanecem pendentes; não declarar a task 3.2h concluída sem a observação do proprietário no browser.
