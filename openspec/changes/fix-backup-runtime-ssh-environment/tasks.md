## 1. Correção e validação

- [ ] 1.1 Confirmar o canal SSH restrito do backup disponível a `production`; se faltar credencial apropriada, documentar provisionamento protegido e obter autorização própria.
- [ ] 1.2 Corrigir o job `operate`, inclusive leitura posterior, e cobrir configuração ausente, igualdade de destino, uso exclusivo do canal protegido e preservação dos modos/fingerprints em testes de política.
- [ ] 1.3 Validar OpenSpec, testes e CI da PR. Após revisão, merge autorizado e CI da main, comprovar inventário somente leitura pelo canal protegido e obter aprovação do novo snapshot antes de tentar `install`.

## Evidence

- A API do GitHub confirmou a ausência de `PRODUCTION_BACKUP_SSH_PRIVATE_KEY` e `PRODUCTION_BACKUP_SSH_KNOWN_HOSTS` no ambiente `production`. O modo protegido `verify-channel` usa somente inventário e precisa passar antes da próxima tentativa de instalação. O job também repete a comprovação do canal antes de cada mutação.
- O instalador relata o SHA e o hash do pacote no recibo JSON e verifica o estado instalado localmente. O workflow valida esse recibo e depois confirma as precondições no inventário sanitizado. O caminho da release não integra esse inventário.
- Guarda de política, Ruff, parse YAML, sintaxe Bash dos steps alterados, OpenSpec estrito e `git diff --check` passaram localmente.

## 2. Diagnóstico da instalação

- [ ] 2.1 Corrigir a perda de diagnóstico observada no run 45596376126. Classificar pelo status SSH e pela resposta estruturada do instalador, sem publicar saída bruta em falha. Preservar o recibo em sucesso e validar o contrato em CI.

- [ ] 2.2 Corrigir a recusa `install_tree_unsafe` reproduzida em Python 3.10 ARM64 com o alias padrão `venv/lib64`. Verificar que o alvo relativo padrão funciona, que desvios continuam bloqueados e que o pacote completo passa no staging offline. Atualizar o pin do wrapper.

Evidência local da task 2.2: em 25/11/2026, a inspeção protegida do host por leitura confirmou a presença da lógica de criação de `lib64` no venv Python 3.10.12 e as precondições anteriores à escrita passaram em uma prova interrompida antes da criação da árvore. O candidato anterior falhou em ambiente Linux ARM64 isolado com `venv --without-pip --copies` seguido de `_privatize_tree`, código `install_tree_unsafe`. A correção preserva o alias relativo e verifica tipo, alvo, proprietário e links. Passaram 48 testes focados em Linux e o ensaio ARM64 offline com o pacote do run 45605080820, incluindo staging, permissões, troca e import posterior. CI da PR e novo gate de produção pendentes.
