# Release coordenado de produção: API + frontend

Este procedimento publica a aplicação Pick-your-Pic usando os serviços `api` e `web` do Compose `markina-gallery`. A execução é manual e requer aprovação específica para SHA, inventário e plano apresentados. Não faz parte de `deploy-homolog` e não concede autorização contínua.

## Alvo documentado — confirmar novamente antes de qualquer execução

- Checkout no host: `/opt/markina-gallery`
- Projeto Compose: `markina-gallery`
- Compose principal: `docker/docker-compose.yml`
- Manifesto observado pelo procedimento web-only: seis arquivos Compose, incluindo overlays em `/var/lib/markina-gallery/deploy-state/`
- Serviços que podem ser atualizados: `api` e `web`
- URL documentada: `https://markina.pickyourpic.com.br`
- Diretório do runtime Compose: `/opt/markina-gallery/docker`
- Arquivo de ambiente documentado: `docker/.env.homolog`; seus valores nunca devem ser exibidos
- Porta observada anteriormente no nginx local: `127.0.0.1:8080`

Esses dados são registros históricos, não confirmação do estado atual. Antes de agir, faça inventário somente-leitura atualizado e apresente serviços/contêineres, IDs de imagem, manifesto, hash de configuração, domínio, portas e recursos compartilhados visíveis. Não altere proxy compartilhado, DNS, firewall, certificados ou outros projetos.

## Elegibilidade e baseline

O procedimento requer checkout limpo em `/opt/markina-gallery`, `origin` correspondente ao repositório aprovado, SHA completo alcançável por `origin/main` e baseline `app-last-healthy.sha` reconciliado. O SHA alvo deve ser descendente do baseline. O diff não pode incluir `backend/migrations/`, `docker/`, arquivos Compose ou `.env*`. Não execute migrations neste fluxo.

O release web-only existente registra somente a versão da web. Esse dado não comprova a origem da API. Portanto, se `app-last-healthy.sha` não tiver um SHA-base de API comprovado e as imagens reais de API/web não tiverem um snapshot conjunto aprovado, o script recusa a operação. Não invente ou copie o marcador web-only como SHA-base da API. O snapshot representa os IDs reais de ambos os serviços e pode capturar uma web mais recente publicada pelo fluxo web-only. A reconciliação inicial exige evidência verificável da API, inventário e aprovação humana explícita antes de registrar o SHA-base e as tags imutáveis do snapshot.

Antes de compilar, o script confere se o filesystem Docker tem espaço livre igual ou superior ao tamanho combinado das duas imagens atualmente ativas. Esse limite é um piso verificável, não uma estimativa de tamanho das imagens novas; se o build exigir mais espaço, ele falha antes de recriar os contêineres.

Os scripts coordenado e web-only usam `production-release.lock`, um lock exclusivo do host. Um lock ocupado ou tentativa `app-in-flight.sha` / `web-in-flight.sha` sem conclusão faz a execução falhar fechada; use o procedimento do fluxo que deixou a tentativa para reconciliar ou reverter.

## Impacto e limites

- Os builds são executados antes de recriar serviços. Uma falha de build não substitui contêineres.
- A execução atualiza `api` primeiro, aguarda healthcheck e então atualiza `web`; Compose não faz uma troca atômica dos dois.
- Uma breve interrupção e uma janela com versões diferentes podem ocorrer; não há garantia de zero downtime.
- PostgreSQL, Redis, workers, nginx, volumes, redes, proxy, DNS, firewall, certificados, ambiente e secrets não são alterados.
- Imagens anteriores são preservadas sob tags imutáveis por serviço e snapshot único. Não há limpeza automática de imagens.
- Uma falha deixa `app-in-flight.sha` e as imagens preservadas para inspeção. Não há rollback automático.
- Rollback também exige inventário e aprovação explícita; restaura os dois serviços, um por vez.

## Reconciliação inicial do baseline

Antes do primeiro release coordenado, é necessário conhecer o SHA da API ativa por evidência confiável de build/deploy. O inventário web-only não prova essa origem. Se ela não puder ser confirmada, pare aqui; não atribua SHA por suposição.

1. Com o host e o serviço/IDs de imagem confirmados em inventário somente-leitura, escolha o SHA da API cuja origem foi comprovada e apresente também domínio, portas, impacto e ausência de recriação de contêineres. Gere o inventário de baseline:

   ```bash
   MARKINA_EXPECTED_REPOSITORY=owner/repo \
     bash scripts/deploy-prod-app.sh --mode baseline-inventory --sha <sha-da-api-comprovado>
   ```

2. Apresente os IDs de API e web e o `approval_code`. Aguarde aprovação explícita do proprietário para registrar esse baseline e tags das imagens. Se qualquer dado mudar, gere inventário novo.
3. Após a aprovação específica, registre o baseline:

   ```bash
   MARKINA_EXPECTED_REPOSITORY=owner/repo \
     bash scripts/deploy-prod-app.sh --mode baseline \
     --sha <sha-da-api-comprovado> --approval-code <codigo-aprovado>
   ```

   O script cria tags imutáveis para os IDs inspecionados e grava `app-last-healthy.sha`/`.snapshot`. Não reconstrói nem recria serviços. Esse passo não é necessário se já houver baseline consistente.

## Inventário e aprovação do release

1. Faça o inventário remoto atualizado em modo somente-leitura e apresente host, projeto, serviços, imagem IDs, configuração, domínio/portas, SHA baseline e alvo, impacto, smoke checks e plano de rollback. Aguarde aprovação explícita dessa execução.
2. Atualize referências no host sem alterar arquivos e confirme checkout limpo:

   ```bash
   cd /opt/markina-gallery
   git fetch origin main
   git status --short
   ```

3. Gere inventário do SHA completo aprovado. `MARKINA_EXPECTED_REPOSITORY` deve corresponder ao `origin` validado:

   ```bash
   MARKINA_EXPECTED_REPOSITORY=owner/repo \
     bash scripts/deploy-prod-app.sh --mode inventory --sha <sha-completo>
   ```

4. Apresente a saída, inclusive IDs das imagens API/web e `approval_code`, sem secrets. Aguarde aprovação explícita do SHA, inventário, domínio, portas, impacto e código. Se o inventário mudar, gere outro e solicite nova aprovação.

## Release aprovado

Execute somente o SHA e código aprovados:

```bash
MARKINA_EXPECTED_REPOSITORY=owner/repo \
  bash scripts/deploy-prod-app.sh --mode release \
  --sha <sha-completo> --approval-code <codigo-aprovado>
```

O script valida novamente inventário e aprovação, adquire lock compartilhado, preserva as imagens atuais de cada serviço, constrói `api` e `web` para o SHA selecionado e atualiza somente esses serviços. Confirma healthchecks de ambos e smoke checks HTTPS `/api/health`, `/healthz` e `/`. Somente após sucesso registra `app-last-healthy.sha`, `app-previous.sha` e `app-history.log`.

## Rollback

Após falha ou regressão, não tente uma publicação nova nem altere outros serviços. Faça o inventário de rollback e apresente os serviços atualmente ativos, imagens preservadas, SHA anterior, domínio/portas, impacto e plano ao proprietário:

```bash
MARKINA_EXPECTED_REPOSITORY=owner/repo \
  bash scripts/deploy-prod-app.sh --mode rollback-inventory --sha <sha-anterior>
```

Depois da aprovação explícita do inventário e código:

```bash
MARKINA_EXPECTED_REPOSITORY=owner/repo \
  bash scripts/deploy-prod-app.sh --mode rollback \
  --sha <sha-anterior> --approval-code <codigo-aprovado>
```

O rollback restaura as duas imagens preservadas e repete os healthchecks e smoke checks. Se qualquer etapa falhar, registre o estado parcial e pare; não declare rollback concluído nem remova o lock/estado por suposição.

## Testes locais

```bash
bash scripts/test_deploy_prod_app.sh
bash scripts/test_deploy_prod_web.sh
python3 scripts/test_deploy_prod_app_policy.py
python3 scripts/test_deploy_prod_web_policy.py
```

Esses testes usam substitutos locais e não acessam o host nem executam release.
