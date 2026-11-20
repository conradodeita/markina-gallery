# Correção do gate de escopo do Picker — 20/11/2026

## Sintoma e causa

A PR #390 foi integrada em `3c6cf8f3a235282af3ae37db50d3d80836765783`. A CI de push `44717212955` recusou o preflight no passo local `Validar escopo e blobs revisados`, com `criterio=arquivo_fora_do_escopo`, antes do inventário remoto. A lista nominal do gate não incluía `.github/workflows/production-google-picker-config.yml` e `scripts/test_production_app_picker.py`, ambos pertencentes à extensão já aprovada. A correção acrescenta somente esses dois caminhos.

## Evidência

- O novo teste de regressão falhou antes da correção com `arquivo_fora_do_escopo` e passou após a inclusão nominal.
- O contrato aceita os dois arquivos aprovados e recusa individualmente workflow semelhante, teste semelhante e worker de backup não revisados.
- Suíte `test_prod_app_release_scope.py`: 28 testes, OK, 217,792 s no Windows. A execução foi isolada das variáveis Git injetadas pelo ambiente do executor, somente no processo de teste; nenhuma configuração Git persistente foi alterada.
- A primeira execução completa teve falhas ambientais após um teste preexistente usar `patch.dict(os.environ, ...)`: os subprocessos Git retornaram `missing config value GIT_CONFIG_VALUE_0`. O diagnóstico de três testes reproduziu a causa; o novo teste executado sozinho passou. Remover somente a configuração Git injetada do ambiente das fixtures permitiu executar a suíte completa sem alteração de código produtivo.
- Ruff nos dois scripts e `openspec validate enable-platform-backup-runtime --strict` passaram; `git diff --check` sem erros.

## Limites

Nenhuma imagem, versão, permissão, segredo, timer, dado ou recurso remoto é alterado por esta correção. Os pins de runtime e a recusa de arquivos não revisados permanecem. A avaliação de refatoração ficou na lista nominal e no teste: não há remoção ou reorganização necessária.

A instalação da ponte e o mount continuam sujeitos ao canal protegido e à evidência de CI correspondente. Não iniciar backup real nem timer. Os diffs locais anteriores permanecem no worktree original, fora desta branch corretiva.
