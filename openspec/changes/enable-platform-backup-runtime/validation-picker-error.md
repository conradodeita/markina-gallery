# Validação — erro no retorno do Google Picker

Data: 20/11/2026

## Sintoma e limite da evidência

O proprietário informou que o diálogo do Google Picker fecha após clicar em `Selecionar`, mas a página não muda e não apresenta a pasta selecionada nem `Autorizar esta pasta`. O navegador não esteve acessível ao executor e o callback real não foi capturado. `Action.ERROR` é uma hipótese plausível, não uma causa confirmada.

## Regressão e correção

- O teste sintético do callback `ERROR` falhava antes da alteração: não havia mensagem visível.
- A correção reconhece `Action.ERROR`, fecha o diálogo e apresenta somente uma mensagem genérica. Não cria candidata, não envia `/picker/authorize` e não exibe o detalhe de erro nem o ID sintético da pasta.
- Validação focada em 20/11: Vitest `google-drive-folder-picker.test.tsx` passou com 3/3 testes; ESLint nos dois arquivos alterados passou; `openspec validate enable-platform-backup-runtime --type change --strict` passou; `git diff --check` passou.

## Validações pendentes ou limitadas

- `npx tsc --noEmit` no worktree reportou erros em tipos gerados em `.next/types` para exports de `calculateWatermarkPreviewFontSize` em `app/admin/settings/page.tsx` e `Trend` em `app/admin/system-monitor/page.tsx`. Esses arquivos de aplicação não foram alterados nesta correção. A CI limpa do candidato precisa fornecer a verificação integrada.
- O build local não foi concluído porque `frontend/node_modules` é um junction para dependências em outro worktree: o Turbopack rejeitou a resolução fora da raiz do projeto e a tentativa com webpack não resolveu pacotes de fontes pelo junction. A CI executa `npm ci` no diretório do candidato e `npm run build`.
- Falta a CI do commit candidato, integração e publicação autorizadas, e uma nova observação do proprietário no browser. Não marcar a task 3.2h como concluída sem confirmação funcional de retorno/erro da seleção.

## Estado operacional

Esta alteração ainda não foi publicada. O destino global permanece `enabled=false`; não houve autorização de pasta, vínculo root-only, backup real ou ativação do timer nesta validação.
