# Tasks

## 1. Diagnóstico agregado

- [x] 1.1 Implementar a consulta read-only para os papéis fixos `api`, `web` e `db`, retornando quantidade total e contagens `running`/`stopped`/`unknown`; cobrir ausência, registro único, duplicidade, estados `created`/`exited`/`dead` e estados desconhecidos com testes de contrato. Evidência: regressão reproduziu ausência da função antes da implementação; suíte atual de inventário passou (17 testes, 1 skip esperado de POSIX/root), incluindo limite de 512 registros por papel.
- [x] 1.2 Cobrir falhas de listagem, inspeção e validação como resultado sanitizado e atômico; provar nos testes que não há contagens parciais, IDs, nomes, labels, saída de comando, caminhos, exceções ou segredos. Evidência: 4 testes de diagnóstico passaram; allowlist de erro do diagnóstico permanece isolada da operação normal; Ruff e `git diff --check` passaram.

## 2. Integração protegida

- [x] 2.1 Expor o diagnóstico como operação nominal read-only no wrapper protegido, vinculada à ponta exata da main e ao lock comum de release, sem argumentos arbitrários; testar que projetos, serviços, comandos e modo `operate` fora da allowlist são recusados. Evidência: teste estático do wrapper passou e Git Bash `-n` validou a sintaxe.
- [x] 2.2 Atualizar pin, manifesto/escopo e testes de CI; criar um job `diagnose` read-only em `production-preflight`, condicionado à main e à CI do SHA exato, que não dependa do preflight com fingerprint, não monte bundle e não acione `operate`; validar também que o inventário normal mantém a exigência de um ID completo por papel. Evidência: teste do workflow, YAML e política de release passaram; suíte do gate de escopo passou (30 testes), com pin do módulo conferido contra seu blob.

## 3. Validação e operação controlada

- [ ] 3.1 Executar testes direcionados e gates de integração aplicáveis, build do artefato Linux ARM64, OpenSpec estrito, verificação de escopo, varredura de segredos e diff check; registrar comandos, resultados e limites de ambiente. Evidência parcial: inventário 17 testes/1 skip esperado; artefato 4; instalador 5/4 skips esperados no Windows; workflow e política de release aprovados; escopo 30 testes; Ruff, YAML, Python embutido, Bash, OpenSpec estrito e diff check aprovados. Gitleaks 8.24.3, checksum verificado, histórico anterior limpo; repetir no commit desta change para incluir o novo snapshot. Build ARM64 ainda pendente. Revisão proporcional de refatoração: helpers de falha e inventário normal preservam consumidores/contrato; nenhum código morto ou duplicação segura para remoção foi identificado.
- [ ] 3.2 Somente após revisão da change, CI verde no SHA exato, preflight atual consistente e autorização operacional específica, instalar pelo canal protegido a referência do wrapper e executar apenas o diagnóstico read-only; registrar contagens agregadas, confirmar que o inventário normal continua recusado pela ambiguidade e verificar `containers_unchanged=true`, sem `operate`, vínculo, ensaio, cópia, restore ou ativação.

## Workflow follow-up

- Revisar a change humanamente antes de sincronizar as specs principais e arquivar.
- Se o diagnóstico confirmar múltiplos registros, reconciliar a causa em change/operação separada, com inventário e aprovação próprios; não selecionar ou remover containers por este diagnóstico.
