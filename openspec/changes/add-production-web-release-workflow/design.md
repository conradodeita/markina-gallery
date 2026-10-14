## Context

Veja `proposal.md` para a motivação. O inventário atualizado confirmou que o host que o proprietário definiu como produção usa `docker/.env.homolog` e seis arquivos Compose: `docker/docker-compose.yml`, `docker/docker-compose.raw-development.yml`, `docker/docker-compose.preview-adjustment.yml`, `docker/docker-compose.system-monitor.yml`, `/var/lib/markina-gallery/deploy-state/branding.compose.yml` e `/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml`. O runtime declara o diretório Compose `/opt/markina-gallery/docker`; o nginx publica `127.0.0.1:8080`, e um proxy compartilhado atende `markina.pickyourpic.com.br`. O job `deploy-homolog` existente pode recriar mais serviços e executar configuração; o novo procedimento não o altera nem o usa.

## Goals / Non-Goals

**Goals:**
- Criar uma rota operacional explícita para release e rollback apenas do serviço `web`.
- Tornar identidade do alvo, SHA, configuração efetiva, portas, domínio, aprovação e evidências verificáveis antes e depois de alterar o serviço.
- Preservar a configuração real já em uso sem revelar ou editar segredos.

**Non-Goals:**
- Renomear, copiar ou editar `.env.homolog`, criar `.env.prod` ou alterar valores de configuração.
- Implantar API, workers, migrations, banco, Redis, nginx, processamento facial ou qualquer recurso do proxy compartilhado.
- Prometer disponibilidade contínua: não há evidência de que exista implantação blue/green para `web`.
- Executar agora o deploy ou rollback no servidor.

## Decisions

1. **Release manual, com escopo fixo em `web`.** O fluxo exige SHA aprovado de `main`, checkout de produção sem alterações locais e projeto/arquivo Compose previamente confirmados. O comando de atualização deve selecionar apenas `web` e evitar dependências, por exemplo usando a semântica equivalente a `up -d --no-deps --build web`. O fluxo de homologação permanece separado. Uma automação que reproduz a rotina atual de homologação foi rejeitada porque pode tocar API, workers, migrations e configuração.

2. **Identificar o runtime pelo manifesto Compose observado.** O script fixa o conjunto e a ordem dos seis arquivos Compose do inventário atual e usa os perfis `facial` e `preview-adjustment` ao resolver a configuração. Confere os metadados do container web, o hash de configuração produzido com `docker compose config --hash web` e o arquivo `.env` fixo sem imprimir valores. A aprovação inclui manifesto, domínio, portas e a divergência do rótulo `homolog`. Qualquer arquivo, diretório, hash ou serviço diferente interrompe a execução para revisão humana.

3. **Separar descoberta, aprovação e mutação.** A primeira etapa é somente-leitura e apresenta host/projeto, containers Markina e estado, SHA saudável/tentativa e alvo, portas, subdomínio, manifesto/configuração sem valores, escopo e rollback. Um código derivado desse inventário é exigido por uma segunda chamada de execução; a chamada recalcula o inventário e recusa se algo mudou. Só então pode reconstruir e recriar `web`.

4. **Não assumir zero downtime.** Recriar um único contêiner pode interromper requisições durante a troca. O procedimento deve informar esse risco e verificar saúde local e smoke tests HTTPS do domínio após a troca. Não deverá modificar Nginx Proxy Manager, DNS, firewall ou certificados para contornar a limitação.

5. **Script de shell acompanhado de runbook.** A automação ficará em `scripts/deploy-prod-web.sh`, com fases separadas de inventário, release, inventário de rollback e rollback; `docs/DEPLOY-PROD-WEB.md` explicará o processo, os dados que devem ser apresentados para aprovação e os limites. Escolhemos esta combinação em vez de apenas comandos manuais para testar guardas de escopo de modo repetível, mantendo a aprovação humana fora da automação.

6. **Rollback pela versão web registrada, sem alterações de dados.** Antes da publicação, o fluxo registra o último SHA saudável e cria uma tag da imagem web corrente vinculada a esse SHA. Em falha, o operador precisa iniciar inventário e aprovação de rollback; o script restaura somente essa imagem e recria apenas `web`. Tags de imagens antigas não são removidas automaticamente. Não há restauração de banco nem execução de migrations neste release.

## Risks / Trade-offs

- [O rótulo `homolog` pode fazer scripts recusarem o alvo ou selecionar configuração errada] → Exigir validação combinada de Compose, serviço ativo, arquivo montado e inventário aprovado; abortar em qualquer divergência.
- [Recriar `web` pode causar breve indisponibilidade] → Informar a janela/impacto possível antes da aprovação e executar smoke tests imediatamente; não anunciar zero downtime.
- [O SHA aprovado não estar no checkout ou build reproduzível falhar] → Validar referência e árvore limpa antes da mutação; falha prévia não deve alterar o contêiner ativo.
- [Smoke test externo falhar por causa do proxy compartilhado ou rede] → Coletar diagnóstico sem mudar recursos compartilhados e permitir rollback somente após avaliação/autorização da etapa de rollback.

## Migration Plan

1. Revisar e aprovar esta change; depois implementar documentação e automação com testes de escopo/guardas, sem conectar-se ao host de produção.
2. Validar localmente que o plano de descoberta é somente-leitura, que a mutação seleciona apenas `web` e que rollback também é restrito.
3. Antes de qualquer execução real, coletar inventário somente-leitura atualizado do servidor e apresentar serviços/recursos, projeto e arquivo Compose, estado atual, porta local, subdomínio `markina.pickyourpic.com.br`, SHA alvo, possíveis interrupções e rollback.
4. Aguardar aprovação humana explícita para o release daquela execução; executar, verificar healthcheck e smoke tests e registrar resultados.
5. Se as verificações falharem, apresentar diagnóstico e plano de rollback, obter aprovação explícita e restaurar somente o SHA web anterior.


## Preparação da integração em main

A preparação autorizada após o inventário segue `integration.md`: base na versão ativa, preservação dos históricos, manutenção de main inerte e PR revisável sem merge/deploy. A diferença de aplicação deve ser avaliada contra o SHA ativo, além da comparação ampla contra main.
