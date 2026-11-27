## 1. Correção e preparação

> **SUPERCEDIDA — NÃO EXECUTAR tarefas pendentes nem despachar workflows.** Este change não deve ser retomado. As caixas vazias são histórico da tentativa cancelada em 25/11/2026; o trabalho vigente está em [retire-platform-backup-runtime](../retire-platform-backup-runtime/tasks.md) e [prove-open-source-backup-and-recovery](../prove-open-source-backup-and-recovery/tasks.md).

- [x] 1.1 Corrigir a leitura do systemd e a atestação da geração Compose da API. Cobrir a ordem observada e a recusa de estados inseguros ou identidade divergente.
- [x] 1.2 Implementar preparo protegido da origem com testemunhas de banco concordantes, fingerprint sob lock e persistência sem sobrescrever vínculo existente divergente. Cobrir preparação repetida, metadados inseguros e falha sem escrita.
- [x] 1.3 Preparar os diretórios fixos do primeiro backup apenas na execução habilitada e proteger a classificação de releases do aplicativo sem relaxar seus gates.
- [ ] 1.4 Validar localmente o fluxo integrado com dados sintéticos e executar CI no SHA da PR. Registrar provas e limites.
- [ ] 1.5 Após revisão e merge autorizado, confirmar CI da main e inventário. Sob autorização operacional, preparar suporte, instalar inerte e atestar a origem antes de renovar a seleção no Picker. Primeira cópia real e timer seguem suas autorizações próprias.

## Evidências de 25/11/2026 BRT

- O workflow `45656452636` aprovou a identidade e o pacote instalados. O vínculo falhou na checagem de inércia antes de alterar a configuração ou acessar o Drive. A inspeção somente leitura no SHA `849bdaeb` confirmou propriedades válidas do systemd em ordem diferente da suposta pelo CLI, API gerida por geração Compose e ausência de `source.json` e dos diretórios de trabalho. A API ativa e o PostgreSQL selecionado confirmaram a mesma identidade física e revisão de schema em consultas de metadados somente leitura.
- Em Linux isolado como root, 52 testes de runtime, configuração, armazenamento e CLI passaram. O teste integrado executou o dispatcher e o sistema de arquivos reais nas etapas de preparação, vínculo, envio, verificação e remoção do item sintético. Docker, systemd e Drive foram simulados nesse teste. A guarda do workflow exercitou a extração privada da testemunha, a fingerprint divergente e a precondição recusada. Passaram também 17 testes do classificador de release e seis de política de CI.
- Ruff, validação OpenSpec estrita das duas changes, sintaxe dos módulos para Python 3.10, parse YAML, `bash -n` e `git diff --check` passaram localmente. A task 1.4 aguarda CI. A task 1.5 aguarda revisão, merge e validação operacional. Nenhuma escrita no host ou Drive ocorreu durante a correção.
