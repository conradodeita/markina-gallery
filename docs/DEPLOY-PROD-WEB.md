# Release de produção limitado ao web

Este procedimento publica ou reverte somente o serviço `web` da Pick-your-Pic. Ele é manual, não faz parte do job `deploy-homolog` e não representa autorização contínua para publicar.

## Identidade conhecida do alvo

- Host: `clearbudget-vnic` (`132.145.193.169`); checkout: `/opt/markina-gallery`
- Projeto/Compose: `markina-gallery`, `docker/docker-compose.yml`
- Diretório Compose do runtime: `/opt/markina-gallery/docker`
- Manifesto ativo:
  - `docker/docker-compose.yml`
  - `docker/docker-compose.raw-development.yml`
  - `docker/docker-compose.preview-adjustment.yml`
  - `docker/docker-compose.system-monitor.yml`
  - `/var/lib/markina-gallery/deploy-state/branding.compose.yml`
  - `/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml`
- Serviço alterável: `web`
- Subdomínio: `https://markina.pickyourpic.com.br`
- Arquivo de variáveis identificado no runtime atual: `docker/.env.homolog`
- Porta local do nginx Markina observada anteriormente: `127.0.0.1:8080`; o proxy HTTPS compartilhado é um recurso externo a este procedimento.

O proprietário confirmou que o host atende produção real, embora o arquivo e as rotinas tenham rótulo `homolog`. O nome não é tratado como prova de que o ambiente seja descartável. A automação valida o manifesto de seis arquivos Compose, o diretório do projeto e o hash de configuração do serviço ativo sem mostrar valores do ambiente; ela aborta em divergência. Se um arquivo, caminho, perfil ou hash mudar, este procedimento precisa ser revisado antes de uso.

O job `.github/workflows/ci.yml:deploy-homolog` atualmente é um fluxo mais amplo, que pode recriar `api`, `web` e `worker`. Ele não é o fluxo de produção definido aqui e não deve ser usado para publicar mudanças em produção. Este runbook não altera o job nem seus segredos.

## Limites e impacto

- O inventário é somente-leitura. A execução requer aprovação explícita para aquele SHA e aquele inventário.
- O comando de mutação é fixado ao serviço `web`, sem dependências; não executa migrations.
- API, banco, Redis, workers, nginx, processamento facial, volumes, redes, proxy compartilhado, DNS, firewall, certificados e arquivos de ambiente ficam fora do escopo.
- O script troca o checkout Git para o SHA durante a operação. Ele exige árvore limpa, guarda o SHA anterior e seleciona somente commits alcançáveis por `origin/main`.
- O script recusa o release se os arquivos de `docker/` diferirem entre o checkout e o SHA alvo, ou se a configuração Compose do `web` divergir do hash do contêiner ativo. Mudanças de Compose precisam de um plano separado.
- A substituição de um único contêiner pode causar uma breve interrupção. Não há garantia de zero downtime.
- O código de aprovação liga o modo, SHA, checkout, versão ativa, contêiner, imagem, hashes de configuração, arquivo de ambiente, host, manifesto, contêiner/portas do nginx e domínio. O script recalcula o inventário antes de mutar e recusa se algo mudou.

## Preparação por execução

1. Colete inventário somente-leitura atualizado dos containers, portas, serviços e recursos. Prepare host, SHA de produção atual e alvo, domínio, porta local, arquivo de ambiente (sem valores), escopo, possível interrupção, verificações e rollback para a aprovação final do passo 4.
2. No preparo autorizado da publicação, atualize apenas as referências Git; isso não troca arquivos do checkout nem serviços:

   ```bash
   cd /opt/markina-gallery
   git fetch origin main
   git status --short
   ```

   A árvore deve estar limpa. Não execute este fluxo se o inventário revelar outro projeto, arquivo Compose, arquivo de ambiente ou host.

3. Gere o inventário do SHA alvo aprovado. `MARKINA_EXPECTED_REPOSITORY` deve conter o owner/repositório correspondente ao `origin` já configurado; não use uma URL de outro projeto.

   ```bash
   MARKINA_EXPECTED_REPOSITORY=owner/repo \
     bash scripts/deploy-prod-web.sh --mode inventory --sha <sha-completo>
   ```

4. Apresente a saída sem acrescentar valores de segredos. A saída inclui `approval_code`; aguarde aprovação explícita do proprietário para esse inventário e código, domínio e SHA exatos. Se o plano mudar, gere inventário novo e solicite aprovação novamente.

## Publicação

Após a aprovação específica do inventário, execute exatamente o SHA e código aprovados:

```bash
MARKINA_EXPECTED_REPOSITORY=owner/repo \
  bash scripts/deploy-prod-web.sh --mode release \
  --sha <sha-completo> --approval-code <codigo-aprovado>
```

O fluxo seleciona o SHA aprovado, compara novamente a configuração efetiva do web, preserva a imagem web atualmente saudável sob uma tag vinculada ao SHA, constrói `web`, executa `up -d --no-deps --no-build web` e valida o healthcheck do contêiner e as rotas HTTPS `/healthz`, `/api/health` e `/`. O código de sucesso registra `web-last-healthy.sha`, `web-previous.sha` e um histórico no diretório de estado da Markina. Uma falha deixa o erro visível e não inicia rollback automático; o registro `web-in-flight.sha` orienta o inventário de rollback.

## Rollback

Após uma falha, examine o resultado e gere o inventário somente-leitura de rollback para apresentar o impacto ao proprietário:

```bash
MARKINA_EXPECTED_REPOSITORY=owner/repo \
  bash scripts/deploy-prod-web.sh --mode rollback-inventory --sha <sha-anterior>
```

Use `--mode rollback-inventory`; o SHA deve ser exatamente o valor registrado em `web-previous.sha`. Esse inventário aceita web unhealthy após falha de smoke test. Apresente o inventário/código e obtenha aprovação explícita do rollback.

Depois da aprovação explícita:

```bash
MARKINA_EXPECTED_REPOSITORY=owner/repo \
  bash scripts/deploy-prod-web.sh --mode rollback \
  --sha <sha-anterior> --approval-code <codigo-aprovado>
```

O rollback restaura a imagem anterior preservada e recria somente `web`, repete healthcheck e smoke tests e atualiza o estado web. As tags de imagem ficam restritas às versões do serviço web; não há limpeza automática de imagens. O procedimento não restaura banco, não executa migrations e não reinicia dependências. Se o healthcheck ou qualquer smoke test falhar, pare e registre o diagnóstico; não tente corrigir o proxy compartilhado por este procedimento.

## Verificações locais

```bash
bash scripts/test_deploy_prod_web.sh
python3 scripts/test_deploy_prod_web_policy.py
```

Esses testes não acessam o host nem executam release.
