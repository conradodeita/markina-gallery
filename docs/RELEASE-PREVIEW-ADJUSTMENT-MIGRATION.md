# Release controlado da migration de intensidade de prévias 0090

Este procedimento publica somente o candidato `0dd015a62447e0c8d4c6af16b381140c8118f2ec`, avançando o schema `20261025_0089` para `20261026_0090`. O baseline operacional registrado para esta change é runtime `c1944189761799be96eeeb921cad9906484d8b09`; qualquer divergência no inventário interrompe o fluxo e exige atualização revisada do plano.

## Escopo e impacto

- A allowlist desde o baseline inclui a migration única de intensidade de prévias, seus consumidores backend/frontend e testes, a documentação correspondente e as atualizações OpenSpec revisadas das PRs #295/#297. O gate rejeita qualquer caminho adicional ou ausente.
- CI obrigatório: execução `push` do workflow `CI` na `main`, para o SHA exato do candidato, concluída com `success`. Uma execução de PR ou de outro SHA não substitui esse gate.
- A migration amplia as restrições de intensidade; não apaga linhas. API e workers Markina são pausados graciosamente durante a janela; o tráfego público recebe resposta 503 temporária, exceto os endpoints de saúde.
- API/web candidatos são construídos antes da barreira. O serviço `db`, Redis, Nginx e workers de terceiros não são recriados. Os workers Markina identificados no inventário são retomados nos mesmos containers.
- Antes do DDL é criado um backup PostgreSQL custom novo, com modo `0600`, SHA-256 e `pg_restore --list`. O arquivo de backup e imagens anteriores são preservados.

## Gates obrigatórios

1. Integrar este fluxo por PR revisada e CI verde. Confirmar o CI do candidato `0dd015a...` separadamente.
2. Instalar e conferir o wrapper SSH root-owned conforme a seção abaixo. Até a conferência de proprietário, modo, hash e pin, o inventário falha fechado.
3. Despachar `preview-adjustment-migration-preflight` em `main`. Ele exige todos os checks do workflow, usa apenas `production-preflight` e retorna inventário sanitizado e fingerprint. Conferir no resumo SHA/runtime, schema, serviços, portas, domínio, backup e HTTPS.
4. Apresentar o inventário, a indisponibilidade temporária, backup e recuperação. O job de release só aceita o fingerprint completo, digitado pelo operador, idêntico ao coletado na mesma execução. O environment `production` continua exigindo sua aprovação protegida.
5. Despachar `preview-adjustment-migration-release` somente após a aprovação humana específica do fingerprint. O executor adquire `production-release.lock` sem espera, revalida inventário/lock e a ponta atual da `main`, e aborta se algo mudou.
6. Após o release, confirmar recibo sanitizado, schema `20261026_0090`, imagens/runtime, saúde dos serviços, smoke HTTPS e preservação dos serviços Markina não alvo. Reconciliar qualquer journal de falha antes de nova operação.

## Atualização do wrapper restrito de preflight

O wrapper instalado em `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper` permanece `root:root`, modo `0755`, com backup anterior e a regra `authorized_keys` `restrict,command=` existente. Não reutilizar a chave mutável de deploy e não acrescentar shell, PTY, forwarding, SFTP ou comandos livres.

Na sessão operacional aprovada após o merge:

1. Baixar `scripts/production-preflight-ssh-wrapper.sh` do SHA integrado da `main` e comparar o conteúdo com a versão revisada do repositório.
2. Conferir o blob Git de `scripts/preview_adjustment_migration_inventory.py` contra `PREVIEW_MIGRATION_INVENTORY_BLOB_SHA` na cópia do wrapper. O comando de preflight aceito é somente `MARKINA_PREVIEW_MIGRATION_SUPPORT_SHA=<40 hex>`.
3. Fazer backup verificável da cópia instalada, substituir atomicamente como `root:root 0755`, conferir SHA-256 e regra SSH preservada. Um comando arbitrário deve continuar sendo recusado sem tocar containers ou banco.
4. O wrapper baixa por HTTPS o arquivo do SHA de suporte imutável, confere o blob pinado e executa exclusivamente Python no modo inventário. Não encaminha stdin nem aceita modo ou argumentos fornecidos pelo cliente.

Esta instalação root-owned não é feita por workflow nem pela PR. Se não puder ser comprovada, não contornar o wrapper com SSH shell.

## Recuperação

- **Antes de invocar Alembic:** restaurar somente os containers de escrita que o executor marcou como tentados, as políticas de restart capturadas e a configuração Nginx anterior; confirmar schema `20261025_0089`. Se alguma restauração falhar, manter o journal e investigar antes de nova tentativa.
- **Depois de iniciar Alembic:** manter tráfego fechado, schema/backup/imagens/journal, não executar downgrade ou `pg_restore` automático. Fazer diagnóstico e obter autorização específica para a ação de recuperação escolhida.
- Não reiniciar, remover, atualizar ou inspecionar profundamente recursos de outros projetos. Toda interação Docker usa o projeto `markina-gallery` e o Compose inventariado.

## Evidência atual

Em 26/10/2026, a execução CI #899 passou para `db839cc67cd55595c8571ab66ef8fc51286bdde1`. A execução #901 (`40384426091`) passou para o SHA candidato mais recente `0dd015a62447e0c8d4c6af16b381140c8118f2ec`; os jobs obrigatórios concluíram com `success`. A execução #899 não substituiu o gate do SHA atual.
