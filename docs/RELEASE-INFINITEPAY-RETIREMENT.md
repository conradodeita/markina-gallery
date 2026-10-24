# Release de aposentadoria InfinitePay

Este procedimento é dedicado à change `release-infinitepay-retirement-prod`. O workflow usa operações manuais separadas de preflight e release, exige `main`, CI e aprovação explícita do inventário/plano com seu fingerprint. O environment `production` sozinho não substitui essa aprovação.

## Pré-condições

- O wrapper SSH `production-preflight` deve estar root-owned, em `0755`, com o blob do script de inventário fixado ao SHA integrado. A chave de preflight só executa inventário.
- O inventário deve comprovar o checkout/runtime alinhado, schema `20261021_0086`, domínio `https://markina.pickyourpic.com.br`, bind Nginx exclusivo `127.0.0.1:8080`, API/web/worker e demais serviços saudáveis, Compose aprovado, smoke HTTPS e binding regular sem symlink, hardlink ou referências compartilhadas.
- O processo exige prova de restauração anterior em um PostgreSQL isolado. Guarde o recibo em `/var/lib/markina-gallery/deploy-state/infinitepay-retirement-restore-test.json`, modo `0600`, usando o backup testado existente em `/var/lib/markina-gallery/backups`. O contrato é:

  ```json
  {
    "result": "passed",
    "database_revision": "20261021_0086",
    "backup_file": "/var/lib/markina-gallery/backups/nome.dump",
    "backup_sha256": "<sha256 do backup restaurado e validado>",
    "tested_at": "2026-10-23T12:00:00Z",
    "isolated": true
  }
  ```

  O recibo não contém dados do backup. O executor confirma checksum, modo e localização; não restaura dados automaticamente.

## Impacto e execução

O executor adquire o lock compartilhado de releases, valida o fingerprint de novo e constrói API/web/worker enquanto a versão atual continua atendendo. Em seguida, interrompe a API e o worker da Markina, cria um `pg_dump -Fc` restrito ao banco Markina, valida o archive com `pg_restore --list`, calcula SHA-256 e evidência agregada de identidade/contagem das tabelas financeiras, aplica somente `20261022_0087` e inicia API/web/worker aprovados. A pausa do worker evita consultas do runtime antigo às colunas removidas; a pausa da API deixa o checkout e o serviço PIX próprio indisponíveis durante a migração. Não é emitida cobrança durante a validação.

O processo não recria Nginx, banco, Redis, workers faciais nem serviços de terceiros e não altera proxy, DNS, firewall, volumes ou redes. O worker geral da Markina é pausado e recriado com API/web para alinhar o ORM ao schema removido. Nenhum prazo de interrupção é prometido: a duração do dump e o tempo de healthcheck dependem do estado real do host.

Depois da migration, o executor confirma schema, imagens, healthchecks locais e HTTPS, compara evidência financeira antes/depois e remove somente o binding cujo inode/metadados foram aprovados, desde que a versão nova esteja saudável e nenhum arquivo Compose encontrado nas raízes `/opt`, `/home`, `/srv`, `/etc`, `/root`, `/mnt` e no diretório de estado da Markina, nem mount bind de container de outro projeto, o referencie. A varredura usa `sudo -n` quando necessário e falha fechada se não conseguir ler uma raiz ou inspecionar todos os containers. As evidências são agregadas; o conteúdo do binding, payloads, nomes e IDs de cliente não são registrados.

## Falhas e recuperação

- Antes de iniciar a migration, a falha restaura o SHA de checkout observado no inventário e, se pausados, inicia os mesmos containers de API e worker anteriores e aguarda saúde. Web só é recriado após a migration; as imagens anteriores ficam preservadas por tags derivadas de seus digests.
- Depois que a migration começa, o executor não executa downgrade nem restauração automática. Mantém o arquivo `infinitepay-retirement-in-flight.sha`, preserva o archive e as imagens antigas e declara o release inconclusivo.
- A recuperação pós-migration é uma operação coordenada separada: reconciliar o estado, obter autorização explícita, restaurar o backup validado somente no banco Markina, restaurar o SHA/imagens anteriores e confirmar saúde. Não usar `alembic downgrade`, `pg_restore --clean`, `compose down`, prune ou remoção de volumes como resposta automática.
- Se o binding for inesperado, compartilhado, symlink/hardlink, alterado desde o inventário ou ainda referenciado, a limpeza física para. O mount removido do Compose não autoriza apagar outro arquivo.

O inventário anterior e a aprovação vinculada são condições obrigatórias. O preflight de 2026-10-24 confirmou schema `20261021_0086`, 11 serviços saudáveis, HTTPS e binding exclusivo da API. Um dump foi restaurado integralmente em PostgreSQL isolado, e o recibo `0600` passou a validação privilegiada, incluindo checksum. O fingerprint aprovado para `f0c28caa` não foi executado: a conferência final encontrou falhas no executor, reproduzidas e corrigidas por quatro cenários locais do corpo real do release. Após integrar a correção, coletar e aprovar novo fingerprint. O wrapper de preflight foi atualizado com cópia anterior verificada; runtime, schema e binding permanecem sem alteração.
