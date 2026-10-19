# Release de produção limitado ao web

## Autorização e escopo

Este runbook prepara a correção de segurança do PR #226. A fase de engenharia não autoriza executar comandos mutáveis na Oracle. Preparação operacional, publicação e recuperação contingencial precisam de uma autorização conjunta específica do proprietário, vinculada ao SHA final integrado, imagem atual e limites abaixo. Depois dessa aprovação, os fingerprints podem ser calculados e consumidos automaticamente dentro desses limites; mudança material exige interromper a operação afetada.

- Checkout: `/opt/markina-gallery`; projeto `markina-gallery`.
- Domínio: `https://markina.pickyourpic.com.br`; bind nginx `127.0.0.1:8080`; web somente em `3000/tcp` interno.
- Serviço que pode ser substituído: somente `web`, sem dependências.
- API, workers, PostgreSQL, Redis, nginx, proxy compartilhado, redes, volumes, fotografias, `.env`, secrets, DNS, firewall e certificados ficam intocados.
- Arquivo de ambiente histórico: `docker/.env.homolog`; é produção real, não ambiente descartável. Não exibir valores.
- Manifestos ativos: `docker/docker-compose.yml`, `/var/lib/markina-gallery/deploy-state/branding.compose.yml`, `docker/docker-compose.raw-development.yml`, `docker/docker-compose.preview-adjustment.yml`, `docker/docker-compose.system-monitor.yml`, `/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml`.
- Possível breve indisponibilidade durante recriação/recuperação do único web. Não há garantia de zero downtime.

O workflow de `develop` publica vários serviços e pode migrar dados. Não usar esse caminho, o PR #177, o release app ou o release facial para esta atualização.

## Identidade e estado

`web-current.identity` é o recibo compartilhado pelos fluxos web e app, em `/var/lib/markina-gallery/deploy-state`. Quatro campos: SHA de origem, ID Docker `sha256:...`, hash Compose web e checkout conhecido. Os scripts conferem imagem/configuração efetivamente executadas com esse recibo. Não usam `web-last-healthy.sha`, `app-last-healthy.sha` ou `last-healthy.sha` para inferir a imagem atual.

`web-previous.identity` identifica a recuperação após release saudável. `web-pending.identity`, `web-pending.services`, `web-pending.compose` e `web-pending.target` e `web-pending.image` preservam imagem, checkout, serviços, arquivos Compose e SHA do procedimento antes do build. O registro pending impede outro release até conclusão/recuperação. O ID atual é preservado sob `markina-gallery-web:rollback-<64 hex do ID>`; a tag precisa resolver ao ID registrado. Tag conflitante nunca é sobrescrita. Tags são referências mutáveis; somente o ID identifica o conteúdo.

Os fluxos app/web usam o mesmo lock existente, aberto somente para leitura e adquirido com flock exclusivo em operações mutáveis. Lock ausente/symlink/ocupado ou tentativa do outro fluxo bloqueia. Inventários não adquirem lock, não escrevem, não fazem fetch e não criam temporários. São snapshots revalidados sob lock antes de qualquer mutação. O snapshot não-web inclui também containers históricos parados, inclusive migrate: ausência de Health/Status é representada por saúde vazia, preservando identidade e estado exited. Isso não executa migration nem permite remover o container como contorno. Erros de inspeção continuam bloqueando.

## Preparação posterior à autorização operacional

Os comandos nesta seção são um roteiro futuro, não evidência de execução. Substituir `SHA_FINAL_APROVADO` pelo SHA exato informado ao proprietário após o merge/CI desta engenharia. Não substituir pelo HEAD de uma branch móvel nem reutilizar automaticamente `81eb0741...`.

1. Conferir por leitura GitHub/Oracle: SHA da main aprovada, CI e ausência de jobs remotos; checkout limpo; 15 serviços saudáveis; imagens/IDs/inícios; bind/domínio; seis Compose e hashes; ausência de tentativas pendentes; imagem atual ligada ao log do release. API APP_VERSION e frontend devem manter Vendas/pagamentos e Estatísticas 404. Confirmar configuração DNS dinâmica do nginx já existente (resolver Docker e proxy_pass por variável), sem reload ou edição. Não executar testes contra dados de produção.
2. Sob a autorização de preparação, obter somente a main no checkout existente, sem trocar a aplicação:

```bash
cd /opt/markina-gallery
APPROVED_SHA=SHA_FINAL_APROVADO
git fetch origin main
test "$(git rev-parse origin/main)" = "$APPROVED_SHA"
git cat-file -e "$APPROVED_SHA^{commit}"
git --no-optional-locks status --porcelain
```

Árvore suja, ponta diferente, código de produto inesperado ou divergência de ambiente bloqueiam. Sem reset, force push, instalação de pacotes, edição de ambiente, limpeza ou troca antecipada de checkout. A rotina não instala o wrapper app remoto.

3. Executar o script do objeto aprovado, permitindo que ele valide também os blobs exatos dos helpers, sem copiar scripts para o checkout antigo:

```bash
run_web() {
  git show "$APPROVED_SHA:scripts/deploy-prod-web.sh" |
    MARKINA_EXPECTED_REPOSITORY=conradodeita/markina-gallery \
      bash -s -- "$@"
}
```

Usar `set -o pipefail` na sessão para também detectar falha no produtor do pipe. Todos os modos recebem `--sha "$APPROVED_SHA"`: é o SHA do procedimento aprovado, inclusive em rollback/recover. A versão/imagem restaurada vêm do recibo, não desse argumento.

4. Caso o recibo esteja ausente, revalidar a origem legada nos logs do release. Evidência de referência (não presumir que ainda esteja atual): release `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`, run #39135274157 tentativa 2, imagem `sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573`. Comparar o ID no runtime e no log; checkout, latest ou marcador isolados são insuficientes. Somente se coincidir com a autorização:

```bash
ACTIVE_SOURCE=fe1f3bc6e1a483bd1ac5f4e71149f903e724873f
ACTIVE_IMAGE=sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573
run_web --mode reconcile-inventory --sha "$APPROVED_SHA" \
  --active-sha "$ACTIVE_SOURCE" --active-image "$ACTIVE_IMAGE"
# Capturar approval_code da saída anterior; não usar um valor antigo.
run_web --mode reconcile --sha "$APPROVED_SHA" \
  --active-sha "$ACTIVE_SOURCE" --active-image "$ACTIVE_IMAGE" --approval-code CODIGO_ATUAL
```

A adoção preserva/confronta o ID e grava recibo/histórico; não troca container nem copia marcadores. Registrar junto à execução a URL do log de origem. Recibo já presente e coerente dispensa adoção. Recibo presente conflitante, symlink ou origem não demonstrável exige investigação; não apagar ou reescrever para contornar o gate.

## Publicação exclusiva do frontend

```bash
run_web --mode inventory --sha "$APPROVED_SHA"
# Conferir snapshot/fingerprint dentro do escopo da autorização conjunta.
run_web --mode release --sha "$APPROVED_SHA" --approval-code CODIGO_ATUAL
```

Antes da primeira escrita, a rotina confirma SHA, raiz/origin, árvore limpa, backend ativo compatível, seis Compose, saúde, identidade, imagens e fingerprint sob lock. Recusa intervalo com mudanças em backend, Docker/Compose, Dockerfile ou dockerignore. Preserva o ID atual e registra pending antes de selecionar checkout/build. Depois do build, repete gates de Git, saúde/configuração, IDs, hashes de arquivos e snapshot não-web; recusa drift antes da recriação.

Constrói somente web e executa `up -d --no-deps --no-build --force-recreate web`. Não executa migration ou comando dentro de API/nginx. Verifica ID construído igual ao executado, hash Compose, saúde, HTTPS `/healthz`, `/api/health`, `/`, `/admin/payments` e 404 em `/admin/statistics`, além do snapshot não-web. Atualiza recibo saudável, histórico e marcador web; limpa pending somente após sucesso. O nginx existente usa resolver Docker com validade de 10 s e variável no proxy do web; retries HTTPS toleram sua re-resolução, sem reload. Falha persistente de roteamento exige recuperar/abortar; não alterar nginx ou redes.

Auditoria runtime zero corresponde ao lockfile integrado, não substitui o build nem prova que os clientes já receberam a correção. Conferir versões do novo build e smoke permitido após publicar. Não efetuar transação financeira/OTP/envio real como teste sem autorização adicional.

## Falha e recuperação contingencial

O script não dispara recuperação automaticamente. A autorização operacional conjunta deverá incluir a execução contingencial abaixo, sem nova pergunta técnica quando os gates permanecem dentro do plano:

```bash
run_web --mode recover-inventory --sha "$APPROVED_SHA"
run_web --mode recover --sha "$APPROVED_SHA" --approval-code CODIGO_DE_RECUPERACAO_ATUAL
```

`recover` usa o pending do release/rollback interrompido. Aceita web unhealthy ou ausente após a troca planejada; recusa imagem corrente diferente do ID anterior e do ID construído registrado. Exige o mesmo SHA de procedimento, imagem e tag anteriores existentes/iguais, seis Compose e serviços não-web inalterados. Não depende de main remota continuar parada; a recuperação permanece vinculada ao código aprovado já local. Restaura imagem padrão pelo ID e checkout original. Se o container anterior continua saudável e usa o ID anterior (por exemplo, build falhou), não o recria. Caso contrário recria somente web e repete saúde/ID/HTTPS/404/snapshot. Falha conserva pending; não declarar recuperação concluída.

Para reverter um release já concluído, usar o recibo anterior com inventário novo:

```bash
run_web --mode rollback-inventory --sha "$APPROVED_SHA"
run_web --mode rollback --sha "$APPROVED_SHA" --approval-code CODIGO_DE_ROLLBACK_ATUAL
```

O rollback posterior depende de estar coberto pela autorização específica. A contingência da mesma janela restaura apenas a versão saudável que existia imediatamente antes da correção. Não restaurar tags históricas `production-web-69965...` ou o par app antigo como atalho. Nenhuma restauração de banco, arquivo, volume, fotografia ou outro serviço está incluída.

## Condições de interrupção

Parar a operação afetada quando: SHA/CI/revisão diferirem; alvo ausente; checkout sujo; provenance ou ID divergir; backup faltar/retag apontar outro ID; houver lock ocupado/tentativa pendente inesperada; Compose/serviço não-web mudar; espaço/build falhar; a imagem executada não for a esperada; saúde/HTTPS/404 não passarem; recuperação não puder confirmar todos os gates. Não contornar proteções, corrigir `.env`, instalar wrapper, recarregar nginx, alterar banco, limpar Docker ou intervir em terceiros.

## Testes fora de produção

`bash scripts/test_deploy_prod_web.sh` cobre sintaxe, política e contratos em fixtures/mocks. `bash scripts/test_deploy_prod_app_services.sh` protege a coordenação do outro fluxo. Testes Linux incluem flock real sobre arquivos temporários locais e falhas de build/saúde/identidade. Nenhum comando Docker/SSH de produção é invocado. Os resultados executados e o CI do SHA final ficam registrados na change `fix-production-web-release-state`.
