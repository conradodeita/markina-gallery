# Validação — erro no retorno do Google Picker

Data: 20/11/2026

## Sintoma e limite da evidência

O proprietário informou que o diálogo do Google Picker fecha após clicar em `Selecionar`, mas a página não muda e não apresenta a pasta selecionada nem `Autorizar esta pasta`. O navegador não esteve acessível ao executor e o callback real não foi capturado. `Action.ERROR` é uma hipótese plausível, não uma causa confirmada.

## Regressão e correção

- O teste sintético do callback `ERROR` falhava antes da alteração: não havia mensagem visível.
- A correção reconhece `Action.ERROR`, fecha o diálogo e apresenta somente uma mensagem genérica. Não cria candidata, não envia `/picker/authorize` e não exibe o detalhe de erro nem o ID sintético da pasta.
- Validação focada em 20/11: Vitest `google-drive-folder-picker.test.tsx` passou com 3/3 testes; ESLint nos dois arquivos alterados passou; `openspec validate enable-platform-backup-runtime --type change --strict` passou; `git diff --check` passou.
- O manifesto de release API/web foi atualizado para fixar o blob exato revisado do seletor (`115e2cc9d7c6ed2ff78ce61acd41cb268edd46ca`, conferido por `git hash-object`); essa reconciliação é necessária para o gate de candidatura e não executa publicação.

## Validações pendentes ou limitadas

- `npx tsc --noEmit` no worktree reportou erros em tipos gerados em `.next/types` para exports de `calculateWatermarkPreviewFontSize` em `app/admin/settings/page.tsx` e `Trend` em `app/admin/system-monitor/page.tsx`. Esses arquivos de aplicação não foram alterados nesta correção. A CI limpa do candidato precisa fornecer a verificação integrada.
- O build local não foi concluído porque `frontend/node_modules` é um junction para dependências em outro worktree: o Turbopack rejeitou a resolução fora da raiz do projeto e a tentativa com webpack não resolveu pacotes de fontes pelo junction. A CI executa `npm ci` no diretório do candidato e `npm run build`.
- A primeira CI do commit `727ecbb1` passou frontend (lint, suíte e build), OpenSpec, Gitleaks e builds das imagens frontend AMD64/ARM64, mas falhou no gate `homolog-inventory-policy` porque o manifesto ainda pinava o blob anterior do seletor. O pin foi reconciliado e aguarda nova CI.
- Após reconciliar o pin, `python scripts/test_production_release_workflow_policy.py` passou (`publication_candidate_ready=true / somente_api_web`) e `python scripts/test_prod_app_release_scope.py` passou com 28 testes. No Windows, os testes desta última suíte exigem `GIT_CONFIG_COUNT=0` no processo local porque o ambiente do Codex injeta configuração Git com um valor vazio; o runner Linux não apresenta essa particularidade.
- Falta a CI verde do commit com pin reconciliado, integração e publicação autorizadas, e uma nova observação do proprietário no browser. Não marcar a task 3.2h como concluída sem confirmação funcional de retorno/erro da seleção.

## Estado operacional

Esta alteração ainda não foi publicada. O destino global permanece `enabled=false`; não houve autorização de pasta, vínculo root-only, backup real ou ativação do timer nesta validação.
