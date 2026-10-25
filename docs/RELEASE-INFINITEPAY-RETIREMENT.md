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

## Publicação concluída em 2026-10-24

Publicado `1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8`, schema `20261022_0087`. API/web/worker saudáveis e nas imagens construídas para o alvo; 11 serviços conferidos e HTTPS aprovado em `/healthz`, `/api/health` e `/`. PIX próprio disponível, cartão desativado. Configuração/credenciais/colunas operacionais, rotas e variáveis de ambiente InfinitePay não existem no runtime novo; o binding exclusivo foi removido e o marcador de execução foi encerrado.

O run `40117699957` passou CI/inventário/aprovação, mas abortou antes da migration porque o worker legado não tratava SIGTERM, recuperando a versão anterior. O proprietário então autorizou indisponibilidade temporária, worker parado, correção pontual e execução direta da etapa final sem repetir CI. O executor local `22f1cdea` validou imagem/source legados, API pausada, filas ativas/elegíveis zeradas e espera ociosa antes de SIGINT; confirmou saída `130`. O worker novo tem parada graciosa normal. Não reclassificar o run falho como verde: a evidência de conclusão é a execução direta e a conferência real do servidor.

O Nginx Markina conservava endereços antigos após recriação: upstreams diretos e `nginx -t` passaram, e reload somente desse container restabeleceu HTTPS. Uma falha de sintaxe no JSON de referências também foi corrigida na limpeza; o helper recusou remoção até os gates de saúde, referência e identidade serem repetidos corretamente.

Backup preservado: `/var/lib/markina-gallery/backups/infinitepay-retirement-20261024T183605Z-1f4483bd6200.dump`, modo `0600`, 110.924.004 bytes, SHA-256 `375b38ea454285d099a4ce043a352abb1321e1044a134bb607f41260e5a2a8ed`. Foi restaurado em PostgreSQL isolado sem rede, portas ou mount persistente. As seis projeções financeiras tiveram contagens/hashes idênticos antes/depois; duas compras InfinitePay confirmadas, 64 pedidos e 64 agrupamentos preservados. Recibo minimizado em `/var/lib/markina-gallery/deploy-state/infinitepay-retirement-financial-proof-1f4483bd.json`; nenhum dado de cliente ou segredo foi exposto.

Container de prova e executor temporário removidos. Identidade web reconciliada com cópia anterior, manifesto API/web avançado ao SHA/schema publicados e contrato emergencial anterior retirado. A PR #281 passou integralmente e foi integrada em `172aef76c6cc971cd81466200da399a6912e90f9`; suas correções e evidências operacionais não exigiram nova publicação da aplicação.

Recibo final restrito: `/var/lib/markina-gallery/deploy-state/infinitepay-retirement-release-1f4483bd.json`, modo `0600`, com resultado `published_healthy`.

## Encerramento operacional e OpenSpec

Em 2026-10-24 o proprietário autorizou concluir os três itens restantes. A PR #281 foi mesclada após CI verde. O wrapper `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper` foi atualizado atomicamente para SHA-256 `96150855a71fe790aa5405cc0de53710e570d2c0768165f9224738316c4373e1`, mantendo `root:root`, modo `0755`, pin app `646852479c83d0bfa356203379a95cbd9e4019f6` e pin de aposentadoria `935af96ec1b650eb2c9ae188186eec38f0dd532b`. A cópia anterior foi preservada e conferida em `/var/backups/markina-gallery/preflight-ssh-wrapper-20261024T1926Z-close-pr281`.

O preflight real pelo wrapper instalado passou em modo somente leitura para `172aef76c6cc971cd81466200da399a6912e90f9`: checkout e runtime mantidos em `1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8`, schema `0087`, API/web saudáveis nas imagens esperadas, bind `127.0.0.1:8080` e os três endpoints HTTPS respondendo `200`. Fingerprint de evidência `07a56b90e3baf3f75a046c42ea2395b08e9a0aa720a01400515d8b746d74b991`; esse valor não autoriza outra publicação. Não foram reiniciados serviços nem aplicada migration nesse encerramento.

As specs de `deployment-operations` e `gallery-sales/infinitepay-retirement` foram consolidadas e conferidas contra todos os requisitos dos deltas (12 e quatro, respectivamente). A validação retornou 23 specs válidas e zero erros. As duas changes foram arquivadas em `openspec/changes/archive/2026-10-24-release-infinitepay-retirement-prod/` e `openspec/changes/archive/2026-10-24-retire-infinitepay-checkout/`, com todas as tarefas concluídas. A integração desse registro é somente documental e não exige deploy.
