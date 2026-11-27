# Recovery protegido de API/web sem Google Picker

Este procedimento é futuro e depende da change `reconcile-picker-free-app-recovery` integrada na `main`, com CI verde para o SHA exato. Ele documenta o fluxo protegido; não autoriza nem executa uma operação em produção.

## Diagnóstico somente leitura

1. No GitHub Actions, abra `Inventariar e recuperar transição API/web` na `main` e despache `diagnose`.
2. Para a primeira recuperação sem Picker, confira `current_reference_api_image` e `current_reference_web_image`. São os IDs de imagem do par registrado, em execução e saudável. Use ambos no ensaio isolado com PostgreSQL sintético e OAuth sentinela. Se as imagens ou a fingerprint mudarem, renove a referência e o ensaio antes da retirada.
3. Examine o SHA e a fingerprint completos apresentados no resumo, a revisão do banco, saúde de API/web, portas/domínio, mounts e witnesses. O diagnóstico não para, renomeia, cria ou remove containers e não altera arquivos ou dados.
4. Se o resultado estiver incompleto, falhar ou mostrar uma identidade/mount inesperado, pare. Não use uma fingerprint antiga nem tente SSH manual.

## Recovery aprovado

1. Obtenha autorização operacional para a fingerprint integral do diagnóstico e para o SHA exato da `main`; a aprovação do environment `production` no GitHub continua obrigatória.
2. Despache `recover` com essa fingerprint. O workflow repete o inventário, valida novamente SHA, CI e destino SSH e aborta antes da mutação se qualquer valor divergir.
3. O helper usa os image IDs e a receita registrados, cria uma geração Compose nova e recupera primeiro a API; só tenta o web depois da API saudável. A receita remove apenas o bind exato `/etc/pyp-google-drive/picker-config.json` → `/run/secrets/google-drive-picker-config.json`. OAuth e os outros mounts permanecem iguais.
4. O container histórico e qualquer candidato anterior são parados e preservados com nome de retenção. O fluxo não os inicia, não remove containers/imagens/volumes, não executa SQL ou migration, não acessa o Drive e não altera outros projetos.
5. O workflow verifica saúde e endpoints antes de gravar o receipt do runtime. Em falha, o journal e os artefatos são preservados; não repita `recover` com o fingerprint anterior. Faça um novo `diagnose` e aguarde revisão e aprovação próprias para a nova fingerprint.

## Depois do receipt saudável

O receipt saudável apenas prova o runtime API/web sem o mount do Picker. A retirada do arquivo do Picker é uma operação protegida separada: exige inventário atual, fingerprint própria e aprovação operacional própria. Essa retirada não alcança OAuth, o diretório pai, banco, dados de clientes, mídias, containers witness ou volumes.

## Validação local sintética

Execute a suíte de contrato a partir de `scripts/` em Linux root (ou CI Linux):

```bash
python -m unittest test_production_app_compose_bridge test_production_app_handoff_inventory test_production_app_handoff_journal test_production_app_handoff_execution test_production_app_handoff_recovery
```

Ela testa os contratos com Docker/SSH simulados e sistema de arquivos temporário. Uma aprovação ou teste local não comprova estado de produção nem libera uma operação remota.

## Obter imagens para o ensaio

Após atualizar o suporte na main revisada com CI verde, despache `export-images` no mesmo workflow de recuperação. A operação repete o diagnóstico e exporta as imagens API/web selecionadas para artifacts `picker-reference-api-<sha>` e `picker-reference-web-<sha>`, com retenção de um dia. Baixe ambos e confira os arquivos `api.sha256` e `web.sha256` antes de importar. Os IDs importados devem coincidir com `image-id.txt` e com o diagnóstico da referência atual. Use PostgreSQL e OAuth sintéticos no ensaio isolado. Artifact de apenas um serviço ou imagem divergente é insuficiente para concluir a task 2.2.
