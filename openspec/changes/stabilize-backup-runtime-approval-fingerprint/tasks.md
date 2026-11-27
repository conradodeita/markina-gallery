# Tasks

> **Registro histórico — contrato de runtime aposentado em 25/11/2026.** A implementação descrita nesta change não deve ser retomada: o código exclusivo foi removido pela PR #436 (`eff4d504`). A retirada remanescente está em `retire-platform-backup-runtime`; a nova prova de backup/recuperação está em `prove-open-source-backup-and-recovery`. Preserve os checkboxes como evidência histórica e preserve a fingerprint genérica dos workflows compartilhados de suporte.

## 1. Fingerprint de aprovação versionada

- [x] 1.1 Implementar projeção canônica e versionada da identidade do host/runtime e dos bindings/capacidades totais de `/var/lib`, `/opt/pyp-backup-runtime` e `/etc/systemd/system`; validar separadamente a conexão autorizada, SHA/CI e pacote no mesmo gate. Falhar fechado para campos ausentes, extras ou inválidos e rejeitar hashes legados. Verificar com testes de mudança de cada testemunha e de invariância dos campos de capacidade voláteis.
- [x] 1.2 Revisar consumidores atuais de `runtime_fingerprint` e a política de refatoração contínua na área afetada; preservar ou remover somente uso comprovadamente substituído. Verificar ausência de duplicação/consumidor quebrado com busca de referências e suíte focada.

## 2. Precondições atuais de capacidade

- [x] 2.1 Calcular limite superior verificável de espaço para arquivos staged, expansão validada dos wheels (limitada a 8 GiB agregados), bytecode/metadados, venv, recibos, runtime anterior preservado e unidades systemd; medir cada filesystem de destino e agregar os que compartilham binding antes da primeira escrita e antes da troca ativa, sob lock. Falhar fechado quando uso projetado não for estritamente inferior a 75%, espaço for insuficiente ou a leitura/bound não puder ser comprovado. Verificar espaço adequado, insuficiente, inválido, destinos compartilhados e redução após staging.
- [x] 2.2 Integrar o gate versionado ao workflow e ao forced command com seus pins de blob, usar v2 somente em `install` e preservar fingerprints integrais em `bind-and-rehearse`/`reconcile`; apresentar ambas as fingerprints conforme a operação, SHA/CI, pacote, percentual e bytes livres por destino em campos distintos e sanitizados. Atualizar o release-preflight para exigir a instalação protegida do wrapper antes do inventário v2; verificar guardas estáticas dos workflows, casos de divergência e `git diff --check`.

## 3. Integração e fechamento

- [x] 3.1 Executar validação OpenSpec estrita, testes focados do inventário/instalador/workflow e gates de qualidade aplicáveis; revisar o diff para confirmar que a alteração se limita ao gate do `install` inerte, sem credenciais, alterações de dados ou efeitos em outros workflows. Registrar comandos, SHAs e limitações no `tasks.md`/`release-preflight.md`; só marcar esta task após evidência completa.

## Workflow follow-up

### Evidência local — 24/11/2026

- Tasks 1.1, 1.2 e 2.2 foram implementadas e verificadas no branch `codex/backup-fingerprint-contract`, sobre a base `bfac44a1a59d81a9830b6d05df3b76b6cec7e109`. `runtime_fingerprint` permanece como guarda de mudança operacional entre leituras do instalador; a aprovação usa o campo v2, e a busca nos consumidores afetados não encontrou duplicação a remover.
- `python -m unittest test_platform_backup_runtime_inventory test_install_platform_backup_runtime -v`: 47 testes executados, 41 passaram e 6 foram ignorados por dependências de POSIX/root indisponíveis no Windows. Um dos skips é a redução de capacidade depois do staging; permanece pendente de execução no CI Linux.
- Passaram a guarda estática `python test_platform_backup_runtime_workflow.py`, Ruff dos cinco arquivos Python alterados, `compileall`, `git diff --check`, `openspec validate stabilize-backup-runtime-approval-fingerprint --strict`, parse YAML dos dois workflows envolvidos e `bash -n scripts/production-preflight-ssh-wrapper.sh`. Os pins do forced command correspondem aos hashes Git dos dois módulos fixados.
- A task 2.1 permanece aberta até o teste POSIX de redução pós-staging ser executado no CI. A task 3.1 permanece aberta até os gates de integração/CI, revisão final do escopo/segredos e registro da evidência no SHA publicado. Até este checkpoint, não houve push, merge, dispatch, SSH, escrita em host/Drive ou operação de produção.

- Rever e aprovar esta change antes de iniciar implementação.
- Após implementação e revisão do código, obter autorização de merge e confirmar CI verde da `main` no SHA exato.
- Atualizar o forced command por seu workflow protegido, após inventário/fingerprint e aprovação específicos; essa instalação não libera o runtime.
- Fazer inventário read-only novo e obter aprovação humana da fingerprint estável, capacidade atual e pacote antes de solicitar a aprovação separada do ambiente `production` para `install` inerte.

### Correção após CI Linux — 24/11/2026

- CI `45517178750`, SHA `41e000890602505a989079d3681607769e832865`: backend (quatro shards), frontend, qualidade, imagens e Gitleaks passaram; o agregado falhou em quatro testes do instalador porque o bound incluía o interpretador real do runner, incompatível com o disco sintético de 100 MB. A falha ocorreu antes dos cenários de transação pretendidos.
- A fixture agora fornece um arquivo de interpretador sintético de tamanho fixo, coerente com a instalação de wheels simulada. Nenhum gate de capacidade do instalador foi relaxado.
- Em Docker Desktop `desktop-linux`, container descartável sem rede, worktree somente leitura e `/tmp` efêmero: `python -B -m unittest test_platform_backup_runtime_inventory test_install_platform_backup_runtime -q` executou 47 testes, todos passaram sem skips. Imagem local de validação `pyp-backup-contract-validation:20261124`, Python 3.13 e Git. A primeira imagem consultada não tinha Git; a execução válida usou imagem própria com Git.
- Tasks 2.1 e 3.1 aguardam confirmação da nova CI no SHA corrigido; nenhuma operação de produção foi executada.

### Fechamento da implementação — 24/11/2026 BRT

- CI `45520382114` concluiu success no SHA exato `f65ffe14556dd6434f259b73ad990bcc04d7f376`: quatro shards backend, backend-quality, frontend, imagens AMD64/ARM64, OpenSpec, Gitleaks e agregados passaram. O log confirma `test_capacity_reduction_after_staging_aborts_before_active_swap ... ok` e os 17 testes do instalador aprovados no Linux.
- Tasks 2.1 e 3.1 concluídas com essa evidência e com a revisão do diff/escopo registrada acima. A implementação está completa na PR #429; revisão humana, autorização de merge, CI da main e gates operacionais posteriores continuam pendentes. A spec principal não foi sincronizada e a change não foi arquivada.
- Nenhum dispatch operacional, acesso ao host/Drive, instalação, backup ou timer foi executado nesta change.
