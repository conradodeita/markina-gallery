# Design

## Context

O script `inventory-homolog-readonly.sh` consulta `git rev-parse HEAD` e compara a revisão com o SHA integral fornecido pelo operador. Em caso de divergência, atualmente encerra sem revelar a revisão encontrada. A proteção evita consultas com a versão de código não confirmada, porém também oculta a única evidência necessária para identificar a origem do estado remoto.

## Goals / Non-Goals

**Goals:**
- Exibir somente os dois hashes de commit ao detectar divergência.
- Preservar a saída de falha e a parada antes de qualquer consulta operacional.
- Provar com teste que nenhum comando Docker é chamado quando os SHAs divergem.

**Non-Goals:**
- Fazer checkout, fetch, reset, merge, deploy, migration, backup, restart ou qualquer escrita remota.
- Expor variáveis de ambiente, configuração renderizada, banco de dados, dados de clientes ou caminhos além do escopo fixo.
- Alterar o fluxo para aceitar SHA diferente do informado.

## Decisions

1. Após validar o formato do SHA esperado e confirmar que o caminho é o checkout fixo `/opt/markina-gallery`, o script exibirá `SHA esperado` e `SHA observado` antes de falhar por divergência.
2. A divergência continuará sendo erro. A mensagem explicitará que nenhuma consulta foi executada; o fluxo não chegará a `docker compose config`, `compose ps` nem ao container transitório.
3. O SHA observado é metadado público de commit do próprio repositório, não credencial. Nenhum outro dado remoto será acrescentado à saída.
4. O teste de política usará um checkout Git temporário com SHA conhecido, exigirá que ambos os hashes apareçam e manterá a asserção de que Docker não foi invocado.

## Risks / Trade-offs

- O SHA observado pode identificar um commit ainda não publicado em `develop`; ele não concede autorização para deploy nem para prosseguir com consultas.
- Uma divergência pode continuar exigindo investigação humana; o diagnóstico apenas informa a revisão para permitir reconciliar o estado.

## Migration Plan

1. Obter aceite humano desta proposta e da delta spec.
2. Implementar o diagnóstico e o teste direcionado; validar Bash, testes de política e OpenSpec strict.
3. Integrar por PR em `main` após CI verde e revisão, sem acionar deploy.
4. Reexecutar o workflow somente leitura com o SHA previamente registrado como esperado. Se houver divergência, usar o SHA exibido apenas para investigação; nenhuma consulta operacional deve ocorrer até uma nova execução explicitamente fixada à revisão confirmada.

## Open Questions

Nenhuma.
