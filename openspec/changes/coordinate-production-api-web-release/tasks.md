# Tasks

## 1. Política compartilhada de release e elegibilidade

- [x] 1.1 Implementar validação do SHA completo alcançável por `origin/main`, checkout limpo, diff sem migrations/configuração de infraestrutura, inventário somente-leitura e aprovação por tentativa; verificar com testes automatizados de aceitação para cada recusa e atualizar o runbook com entradas, saídas e proteção contra exposição de secrets. Evidência: `scripts/test_deploy_prod_app.sh` cobre checkout sujo, SHA ausente/fora de main, migrations/configuração, estado SHA inválido e aprovação divergente; `scripts/test_deploy_prod_app_policy.py` confere escopo e ausência de secrets no runbook.
- [x] 1.2 Implementar lock exclusivo do host compartilhado entre release coordenado e web-only, com falha fechada para operação concorrente ou tentativa interrompida; verificar com teste simulado de lock ocupado/reconciliação e atualizar ambos os procedimentos. Evidência: shell test simula lock ocupado e marcador de tentativa de cada fluxo; testes/policies web e app confirmam o mesmo arquivo de lock e que os dois scripts o adquirem.
- [x] 1.3 Implementar inventário e registro inicial do baseline com confirmação de origem, código de aprovação e gravação limitada a estado/tags; verificar que divergência recusa sem recriar contêineres e documentar o bootstrap manual aprovado. Evidência: shell test rejeita código incorreto, aceita o caminho simulado de tag/estado e verifica que o bootstrap não chama `compose up`; runbook descreve aprovação e prova de origem.

## 2. Release coordenado de API e frontend

- [x] 2.1 Implementar build prévio de `api` e `web` para o mesmo SHA, registro das imagens e referências atuais por serviço e validação de espaço/imagens de rollback; verificar que falhas de build ou pré-condições não recriam contêineres. Evidência: shell tests simulam build dos dois serviços, tag ocupada, build falho sem `up` e filesystem com espaço suficiente/insuficiente; policy confirma tags por serviço/snapshot.
- [x] 2.2 Implementar atualização limitada a `api` e `web`, ordem API depois web, healthchecks individuais, smoke checks HTTPS e registro auditável da tentativa conjunta; verificar sucesso e falhas injetadas sem mutar produção. Evidência: shell tests verificam API→health→web→health→smoke e que falha de API ou smoke mantém tentativa aberta sem marcar saúde; policy restringe mutação Compose aos dois serviços.
- [x] 2.3 Implementar rollback conjunto sob aprovação explícita, restaurando os identificadores anteriores específicos de cada serviço e repetindo healthchecks/smoke checks; verificar rollback completo, rollback parcial e registro de resultado. Evidência: shell tests verificam restauração dos dois snapshots e interrupção após falha de API sem avançar web ou declarar sucesso.

## 3. Compatibilidade, documentação e validação integrada

- [x] 3.1 Atualizar testes e procedimento web-only para obter o lock compartilhado e rejeitar mudanças que dependam de API, preservando sua mutação exclusiva de `web`; verificar sucesso, concorrência e recusa por incompatibilidade. Evidência: `scripts/test_deploy_prod_web.sh` cobre recusa antes de selecionar SHA quando há diff em `backend/`; policy verifica lock e mutação web-only; teste shell prévio do fluxo continua aprovado.
- [x] 3.2 Documentar release, pré-requisitos, inventário atual requerido, código de aprovação por execução, janela de interrupção, logs sem secrets e rollback em runbook; verificar cada comando do runbook em ambiente isolado ou modo simulado. Evidência: `scripts/test_deploy_prod_app_policy.py` confere os modos baseline/release/rollback, gates, ausência de segredos e limites de disponibilidade nos runbooks de app e web.
- [x] 3.3 Executar testes locais de ambos os caminhos, validação shell/policy e `openspec validate --strict`; registrar evidências e revisar o diff para confirmar que nenhuma execução de produção, migration ou alteração de ambiente ocorreu. Evidência: `test_deploy_prod_app.sh`, `test_deploy_prod_app_policy.py`, `test_deploy_prod_web.sh` e `test_deploy_prod_web_policy.py` passaram; `bash -n`, `py_compile`, `openspec validate --strict` e `git diff --check` passaram; a revisão confirmou escopo restrito aos scripts/runbooks/OpenSpec e nenhuma conexão, migration, escrita em `.env` ou mutação de produção.

## Workflow follow-up

- Revisar a change e aprovar o início da implementação antes de alterar código.
- Após implementação completa e validada, solicitar revisão humana; sincronizar a spec principal e arquivar somente após essa revisão.
- Antes de qualquer release real, apresentar inventário remoto atualizado, domínio/portas, SHA, serviços afetados, plano de impacto e rollback para aprovação explícita daquela execução.
