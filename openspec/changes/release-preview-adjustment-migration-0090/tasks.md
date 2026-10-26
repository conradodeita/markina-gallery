# Tasks

## 1. Escopo, preflight e recuperação

- [ ] 1.1 Atualizar o verificador para aceitar somente a transição `c194418...`/`20261025_0089` para o candidato integrado `0dd015a...`/migration `20261026_0090`, incluindo apenas a allowlist revisada de prévias e das PRs #295/#297; conferir ancestralidade, CI verde, cadeia Alembic e schema com testes válidos e divergentes.
- [x] 1.2 Criar inventário remoto somente-leitura com fingerprint sanitizado, serviços/health, Compose e overlays efetivos, portas/domínio e backup verificável; validar saída minimizada, omissões e falhas fechadas com regressões. Evidência: `python -m py_compile` passou; sete testes sintéticos cobrem fingerprint, campos ausentes/extras (segredos), divergências de SHA/schema/migration/runtime, serviços/portas, Compose, backup, HTTPS, seleção de CI exata e CI pendente/falha. O acesso ao host fica reservado ao task 4.2 após merge e instalação do wrapper pinado.
- [x] 1.3 Criar executor de release que exija fingerprint aprovado, lock exclusivo, parada graciosa e ociosidade dos escritores, backup validado, `alembic upgrade 20261026_0090` explícito e recovery sem downgrade automático; simular falhas antes/depois de DDL. Evidência: 10 testes focais passaram; cobrem fingerprint, ordem backup→DDL→runtime, falhas pré/pós-DDL, fence, parada graciosa e revisão Alembic explícita. O validador de backup é exercitado por política `pg_restore --list`; nenhuma restauração real foi executada nesta fase local.

## 2. Integração protegida

- [ ] 2.1 Adicionar operações manuais separadas de preflight e release no workflow, com credenciais distintas, proteção `production`, CI completo, SHA/fingerprint exatos e sem disparo em PR; validar política para nenhum job mutável fora da operação aprovada. Implementação e teste da política passaram; o CI desta change ainda é necessário.
- [ ] 2.2 Atualizar o wrapper root-owned via contrato versionado e pin de blob do helper exato, preservando chave restrita; testar recusa de shell/comandos arbitrários e registrar procedimento de instalação/conferência no runbook. Código/pin versionados, simulação da chave restrita e runbook implementados; a cópia root-owned ainda depende da integração e instalação operacional da task 4.1.
- [x] 2.3 Atualizar runbook e evidências para o runtime `c194418...`, schema `0089`, candidato `0dd015a...`, inclusão revisada das PRs #295/#297, impactos, backup e recuperação; validar que não há segredos ou dados de cliente. Evidência: runbook dedicado e atualização do procedimento do wrapper; revisão textual de escopo, sem segredos nem payloads de cliente.

## 3. Validação e revisão

- [ ] 3.1 Executar testes direcionados dos scripts, gates, backup/restore isolado e cenários de falha; corrigir regressões e registrar resultados reproduzíveis. Testes focais e policy passaram; a suíte completa `scripts.test_prod_release_state` ficou bloqueada no harness de RPC Bash no Windows (processos de teste suspensos sem tráfego RPC). Repetir no runner Linux/CI; nenhuma operação de backup ou restore real foi feita.
- [ ] 3.2 Obter CI verde para o SHA da change, revisar diff e validar OpenSpec em modo estrito e `git diff --check`.

## 4. Publicação protegida

- [ ] 4.1 Integrar o fluxo após PR revisada e CI verde; instalar e conferir a atualização root-owned do wrapper segundo o runbook, sem ampliar a chave SSH.
- [ ] 4.2 Executar apenas o preflight read-only no host e registrar serviços, schema, portas, domínio, backup e fingerprint; apresentar o plano de impacto zero e aguardar aprovação do fingerprint exato.
- [ ] 4.3 Após aprovação explícita do inventário atual, executar o release; validar schema `20261026_0090`, runtimes, healthchecks, smoke HTTPS e preservação dos serviços de terceiros antes de registrar conclusão.
