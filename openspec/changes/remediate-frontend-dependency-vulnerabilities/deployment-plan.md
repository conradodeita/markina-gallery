# Plano de publicação da correção do frontend

## Escopo proposto

- Aplicação: Markina Gallery, domínio `markina.pickyourpic.com.br`.
- Projeto Compose documentado: `markina-gallery`, arquivo `docker/docker-compose.yml`.
- Entrada documentada anteriormente: porta pública `8080`; frontend na porta interna `3000`.
- Serviço pretendido: somente `web`/frontend, para incluir o lockfile corrigido; sem banco, migrations, mídia, índice facial, segredos, worker, Redis, proxy ou containers de outros projetos.

## Inventário atual

Inventário remoto somente-leitura em 14/10/2026, via sessão SSH fornecida pelo proprietário:

- Host: `132.145.193.169` (`clearbudget-vnic`), usuário `ubuntu`.
- Compose `markina-gallery`: 15 serviços em execução e saudáveis; redes e volumes permanecem sob o projeto dedicado.
- Nginx: `127.0.0.1:8080` publicado para `80/tcp` interno.
- Frontend `web`: saudável em `3000/tcp`, sem porta publicada no host e sem volumes montados.
- A etiqueta de configuração Compose do projeto referencia `/opt/markina-gallery/docker/.env.homolog`. O inventário operacional anterior em `../fix-facial-search-latency/deployment-plan.md` confirma que este host serve `https://markina.pickyourpic.com.br` com dados reais. Tratar o ambiente como contendo dados reais independentemente do nome do arquivo.
- O Nginx usa `server_name _` e encaminha tráfego aos serviços `api` e `web`; não foi feita leitura de configuração de segredos.

O nome `.env.homolog` é uma convenção histórica do arquivo, não evidência de que os dados sejam descartáveis. Nenhum container foi reiniciado ou alterado durante o inventário.

## Impacto e rollback previstos

Uma futura atualização substitui somente a imagem/instância do frontend pelo build do commit aprovado, preservando as portas e o domínio. A configuração anterior da imagem deverá permanecer disponível para rollback do serviço `web`. Nenhuma operação em banco ou volumes está prevista.

## Gate

O merge em `develop` aciona `.github/workflows/ci.yml` e `scripts/deploy-homolog.sh`; o script constrói `api`, `web`, `worker` e `migrate`, pode parar os escritores e aplica migrations. Esse fluxo amplo não corresponde ao escopo desta correção. Publicar somente `web` requer uma rota revisada `--no-deps` que consuma o commit aprovado, preserve os overlays ativos e não execute `migrate`, workers, proxy ou demais containers. O CI de PR e a revisão humana precisam terminar antes dessa operação. O inventário desta execução foi somente-leitura.

## Candidato local baseado em `main` — 18/10/2026

Para preparar a atualização da versão efetivamente utilizada em produção sem carregar a árvore de `develop`, foi criada a branch local `codex/remediate-frontend-vulnerabilities-main-2026-10-18`, iniciada em `origin/main` `b405f11531515d7672c9683010a6fa3851fe8353`. Foram reaplicados somente os commits de dependências e do gate operacional do PR #177. O HEAD do candidato durante a validação foi `8df2eb69a09dbed51ae1ad2f22afe7e8869da75c`; nessa preparação inicial a branch ainda não estava publicada.

O diff do candidato contra `main` contém `frontend/package.json`, `frontend/package-lock.json` e os cinco artefatos desta change OpenSpec. Não altera `backend/`, migrations, Docker/Compose ou regras de produto. O build mantém `/admin/payments` e não gera `/admin/statistics`, preservando a aposentadoria da página já presente em `main`.

Auditorias do lockfile da linha atual de `main` registraram 3 vulnerabilidades de runtime (2 altas e 1 crítica) e 11 no total (10 altas e 1 crítica). No candidato, `next` e `eslint-config-next` resolvem para `16.4.0`, `sharp` para `0.35.5` e `source-map-js` para `1.2.2`; `npm audit --omit=dev` retornou zero vulnerabilidades. `npm audit` completo permanece com 5 altas em `braces@3.0.3`, somente na cadeia de desenvolvimento do ESLint. O conserto automático propõe downgrade incompatível de `eslint-config-next` para `14.2.35` e não foi aplicado.

Validação local do candidato: `npm ci` instalou 439 pacotes; `npx tsc --noEmit`, `npm run lint` (0 erros, 34 avisos), `npm run build` e `npx -y @fission-ai/openspec@1.14.0 validate --strict --all` passaram (121 itens, 0 falhas). A primeira execução completa do Vitest teve 1 falha em 562 testes; o teste isolado e o arquivo completo passaram, e uma segunda execução completa passou com 63 arquivos e 562 testes. A falha transitória ocorreu durante execução paralela do build/lint e não foi alterado código de produto.

## Procedimento web-only verificado na linha `main`

O script `scripts/deploy-prod-web.sh` em `main` confirma o repositório, SHA de produção, hashes dos seis arquivos Compose ativos e estado saudável do contêiner `web`; recusa SHA que não seja ancestral de `origin/main`, mudanças em `backend/`, divergência de configuração, lock ocupado ou tentativa de release pendente. A mutação compila somente `web` e executa `docker compose ... up -d --no-deps --no-build web`; não chama `migrate` nem recria API, workers, banco, Redis, nginx, proxy, redes ou volumes. Preserva a imagem anterior, valida saúde do contêiner e HTTPS em `/healthz`, `/api/health` e `/`, e registra os SHAs para rollback. Pode haver breve interrupção do frontend.

O candidato ainda não é ancestral de `origin/main`; portanto, não é alvo válido para o script enquanto não for integrado à linha protegida. A publicação operacional exige primeiro CI e revisão humana do PR de `main`, depois novo inventário somente-leitura do estado ativo e autorização específica para o SHA e código de aprovação exibidos por `--mode inventory`. Nenhum inventário de release, comando de mutação, merge, push desta branch ou deploy foi executado na preparação inicial.

O classificador da linha `main` foi executado contra o candidato com base `b405f11531515d7672c9683010a6fa3851fe8353`; ele reportou baseline de produção `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f` e `release_scope=none`. Assim, um push futuro desta mudança por si só não habilita os preflights/releases automáticos de API, facial ou app; o CI normal de `main` ainda executaria. O deploy web continua manual pelo procedimento e gate descritos acima.

Os testes locais do procedimento também passaram: `bash -n scripts/deploy-prod-web.sh`, `bash scripts/test_deploy_prod_web.sh` e `python scripts/test_deploy_prod_web_policy.py`. O harness usa stubs para Compose e Docker; não acessa o servidor nem executa uma operação de release.

## Publicação controlada para revisão em `main` — 18/10/2026

O proprietário autorizou explicitamente o push desta branch e um novo PR exclusivamente para `main`, com acompanhamento dos checks e Code Review. Merge, deploy, acesso ou alterações na Oracle, migrations, dados, containers, limpeza e mudanças de regras de negócio ficaram fora da autorização. Essa autorização não altera o gate operacional da task 3.2.

Após `git fetch origin`, o candidato permaneceu limpo em `1f1c65b0cfada8525bff3f92c187ae7e10b521ed` e `origin/main` permaneceu em `b405f11531515d7672c9683010a6fa3851fe8353`, sua base ancestral. O push criou a branch remota sem force push ou reescrita. O PR de revisão é https://github.com/conradodeita/markina-gallery/pull/226, base `main`, aberto e sem auto-merge. O PR #177 para `develop` permanece aberto no head `e9ce8405c1d53b8015e72b7f1f55a098329b3926`.

O diff contra `main` contém somente `frontend/package.json`, `frontend/package-lock.json` e os cinco artefatos desta change. A comparação de `frontend/` (exceto os dois manifests), `backend/`, `docker/` e `.github/` contra o baseline de produção documentado `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f` não apresenta diferenças. A árvore mantém Vendas e pagamentos e não contém a rota `/admin/statistics`. Nenhum arquivo de aplicação foi modificado nesta etapa.

Os workflows versionados e o cadastro remoto foram conferidos. `ci.yml` executa CI isolado em `pull_request`; seu gatilho `push` cobre somente `develop` e `main`. `deploy-homolog` exige push em `develop`; os preflights/releases exigem push em `main` ou execução manual e os rollbacks são manuais. Os outros três workflows versionados são somente `workflow_dispatch`; não há cadeia `workflow_run`/`workflow_call` nem `pull_request_target`. O cadastro remoto conserva um registro antigo de `remote-test-smoke.yml`, cujas últimas execuções foram pushes em outra branch em 08/10; o arquivo inexiste em `main` e neste candidato e não participa deste PR. Os testes de políticas e de migrations do CI usam stubs ou bancos sintéticos do runner, sem acessar a Oracle. A seleção JEV foi usada para localizar a evidência dos workflows, seguida de leitura dos trechos e inventário exato dos gatilhos.

A auditoria foi repetida no candidato publicado: `npm audit --omit=dev --json` terminou com código 0 e zero vulnerabilidades; `npm audit --json` terminou com código 1 devido aos cinco achados altos de `braces` na cadeia de desenvolvimento já descrita, sem críticos. O classificador executado no SHA `1f1c65b0cfada8525bff3f92c187ae7e10b521ed` retornou novamente `release_baseline_sha=fe1f3bc6e1a483bd1ac5f4e71149f903e724873f` e `release_scope=none`.

O conector Code Review solicitou conexão da conta GitHub e não forneceu uma revisão. Como alternativa disponível, foi executado `codex review --base origin/main` pelo CLI local, com sandbox somente leitura, contra o candidato `1f1c65b0cfada8525bff3f92c187ae7e10b521ed`. O processo terminou com código 0 e sem defeitos acionáveis no diff. O registro desta publicação modifica somente os dois documentos OpenSpec; não altera o código revisado.

O CI e seus resultados por SHA devem ser consultados em https://github.com/conradodeita/markina-gallery/pull/226/checks. Integração futura exige todos os checks do head final aprovados, revisão humana e autorização específica para merge em `main`. Antes dessa integração, conferir novamente o avanço de `main` e o classificador. Depois do merge autorizado, resolver o SHA efetivo em `main`, obter autorização para novo inventário somente leitura e apresentar o inventário, portas/subdomínio e plano de impacto limitado a `web`; qualquer deploy exige uma autorização operacional posterior específica para o SHA e código de aprovação. Uma eventual publicação pode interromper brevemente o frontend e deve preservar a imagem anterior para rollback.
