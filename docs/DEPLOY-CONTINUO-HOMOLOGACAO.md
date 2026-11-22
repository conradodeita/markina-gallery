# Retomada da aplicação em produção — utilitário com nome legado

> Não existe ambiente operacional de homologação. O fluxo antigo de deploy contínuo em `develop` e o job `deploy-homolog` foram aposentados. Este arquivo mantém somente o procedimento restrito de retomada de contêineres existentes da produção; não configure o Environment `homolog`, secrets `HOMOLOG_*` nem publique a partir de `develop`.

## Escopo e nomes históricos

- O utilitário `scripts/resume-homolog.sh` e o caminho `docker/.env.homolog` mantêm nomes históricos. O destino configurado pelo script é a produção real em `/opt/markina-gallery`, projeto Compose `markina-gallery`; não há um segundo ambiente.
- Este procedimento só pode iniciar contêineres da aplicação que já existem, depois de uma parada controlada, com autorização operacional explícita e após confirmar que checkout, imagens e schema correspondem à última versão saudável.
- Ele não faz release, build, recriação, migration, rollback de versão, limpeza, alteração de banco ou mudança em serviços vizinhos.
- Para releases, migrations ou rollback, use `DEPLOY.md`, o runbook específico da operação e a change OpenSpec vigente. Este procedimento não substitui esses gates nem autoriza uma publicação.

## Retomada sem deploy ou migration

Antes de executar, confirme no inventário atual que PostgreSQL e Redis exclusivos da Markina estão saudáveis, que o checkout e as imagens já correspondem ao SHA saudável e que a revisão Alembic do banco é o único head presente no checkout. Se qualquer condição divergir, não execute o script; siga o runbook da operação autorizada.

No host de produção, somente depois da autorização aplicável e da confirmação de escopo:

```bash
cd /opt/markina-gallery
bash scripts/resume-homolog.sh --public-base-url https://markina.pickyourpic.com.br
```

O script confirma o diretório do projeto, a configuração externa sem exibir seus valores, a saúde das dependências e a revisão do banco. Em seguida, inicia somente os contêineres existentes da aplicação com `docker compose up -d --no-deps --no-recreate` e aguarda healthchecks locais e públicos. Não inicia PostgreSQL, Redis, Evolution, Proxy Manager ou serviços vizinhos; não usa `docker compose start`, migration, `docker compose down` ou prune.

Se o preflight, a revisão do schema ou qualquer healthcheck falhar, preserve o estado para diagnóstico e interrompa. Não tente limpar ou recriar contêineres por este procedimento.
