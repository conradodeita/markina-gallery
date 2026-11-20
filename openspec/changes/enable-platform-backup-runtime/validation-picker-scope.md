# Correção do gate de escopo do Picker — 20/11/2026

## Sintoma e causa

A PR #390 foi integrada em `3c6cf8f3a235282af3ae37db50d3d80836765783`. A CI de push `44717212955` recusou o preflight no passo local `Validar escopo e blobs revisados`, com `criterio=arquivo_fora_do_escopo`, antes do inventário remoto. A lista nominal do gate não incluía `.github/workflows/production-google-picker-config.yml` e `scripts/test_production_app_picker.py`, ambos pertencentes à extensão já aprovada. A correção acrescenta somente esses dois caminhos.

## Evidência

- O novo teste de regressão falhou antes da correção com `arquivo_fora_do_escopo` e passou após a inclusão nominal.
- O contrato aceita os dois arquivos aprovados e recusa individualmente workflow semelhante, teste semelhante e worker de backup não revisados.
- Suíte `test_prod_app_release_scope.py`: 28 testes, OK, 217,792 s no Windows. A execução foi isolada das variáveis Git injetadas pelo ambiente do executor, somente no processo de teste; nenhuma configuração Git persistente foi alterada.
- A primeira execução completa teve falhas ambientais após um teste preexistente usar `patch.dict(os.environ, ...)`: os subprocessos Git retornaram `missing config value GIT_CONFIG_VALUE_0`. O diagnóstico de três testes reproduziu a causa; o novo teste executado sozinho passou. Remover somente a configuração Git injetada do ambiente das fixtures permitiu executar a suíte completa sem alteração de código produtivo.
- Ruff nos dois scripts e `openspec validate enable-platform-backup-runtime --strict` passaram; `git diff --check` sem erros.

## Reconciliação da base publicada

A leitura SSH de 20/11/2026 confirmou API `2cd9ce58395d`, imagem `sha256:c3963cab482c4cfe384907b71d387d61afeec26eeb16c9ac8b979a5f6cc312ec`, saudável, APP_VERSION `f18db9f22bb75a549e7c4289bff38bf3a880f7f2`, APP_ENV production e flag facial true. Web `23109e30a9d9`, imagem `sha256:7f6c377ac817615680ae6d47bc493a3287fa78bc7695d5ef6152beac23d35ada`, saudável. Checkout e `app-last-healthy.sha` coincidem com f18db9f2; `web-current.identity` vincula esse SHA à mesma imagem e hash semântico `53ff53db56d6fdf31a22db71afd5e4e3ac8ea3d3d3b5d0a63bce26418534991b`. O label histórico da imagem web continua bfe511f; a identidade publicada é comprovada pelo recibo e digest, sem inferir versão pelo label.

O manifesto ainda declarava bfe511f como base, anterior à publicação comprovada. Atualizar somente `production_baseline_sha` para f18db9f2 reconcilia a classificação com a produção atestada. Não há diff em backend/app, frontend ou docker entre f18db9f2 e esta correção; os pins de runtime permanecem idênticos. O Picker ainda não está montado. A leitura não modificou recurso remoto.

Os 16 testes de classificação passaram (4,353 s). A execução no histórico real em `0c96770b` retornou `release_baseline_sha=f18db9f2`, `release_scope=none` e `app_release_ready=true`.

## Reconciliação da asserção operacional

O run `44719615965` passou backend, frontend, builds e contratos de escopo/classificação. O agregador recusou apenas a asserção estática da base em `test_production_release_workflow_policy.py:565`, ainda fixada em bfe511f. A asserção foi atualizada para f18db9f2, comprovado pelos recibos e imagens acima, mantendo a exigência de SHA exato; nenhuma regra foi removida. O contexto legado gemma-runtime apenas propagou a falha do agregador.

A política completa executada localmente após a correção retornou `publication_candidate_ready=true / somente_api_web` e `production release workflow policy: ok`; Ruff e diff check passaram.

## Proteções

Nenhuma imagem, versão, permissão, segredo, timer, dado ou recurso remoto é alterado por esta correção. Os pins de runtime e a recusa de arquivos não revisados permanecem. A avaliação de refatoração ficou na lista nominal e no teste: não há remoção ou reorganização necessária.

A instalação da ponte e o mount continuam sujeitos ao canal protegido e à evidência de CI correspondente. Não iniciar backup real nem timer. Os diffs locais anteriores permanecem no worktree original, fora desta branch corretiva.
