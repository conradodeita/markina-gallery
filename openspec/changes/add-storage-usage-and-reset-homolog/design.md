## Context

Veja `proposal.md` e os dois delta specs. A rota administrativa `/admin/validation-summary` já alimenta a Visão geral, mas não mede arquivos. O inventário operacional já soma `source`, `derivatives` e `history`, porém existe somente como comando restrito de homologação. A rotina destrutiva atual preserva admin/configurações e limpa as raízes operacionais corretas, mas sempre cria um dump antes da exclusão.

O ambiente alvo continua sendo `/opt/markina-gallery`, projeto Compose `markina-gallery`, entrada exclusiva `127.0.0.1:8080` e subdomínio `markina-homolog.duckdns.org`. A solicitação atual declara os dados de teste descartáveis e dispensa um novo backup; isso não autoriza apagar backups antigos nem qualquer recurso fora do projeto.

## Goals / Non-Goals

**Goals:**

- expor bytes fotográficos reais e quantidade de fotos numa projeção administrativa agregada;
- manter a Visão geral rápida e utilizável se a medição física falhar;
- executar uma única limpeza homologada sem novo dump, com gates mais estritos que o modo comum;
- provar preservação de conta/sessão administrativa e preferências globais.

**Non-Goals:**

- medir banco, imagens Docker, modelos faciais, logs, backups ou uso total do filesystem;
- detalhar uso por cliente, galeria, pasta ou arquivo;
- criar migration, política automática de limpeza ou botão destrutivo no painel;
- apagar backups preexistentes ou recursos de outros projetos.

## Decisions

### 1. A projeção existente receberá um bloco `storage`

`/admin/validation-summary` continuará sendo a única consulta inicial da Visão geral e acrescentará `storage.photo_count`, `storage.bytes` e `storage.available`. A contagem virá de `COUNT(photo_asset.id)`; os bytes virão do filesystem. O contrato não retorna breakdown, paths nem nomes.

Alternativa descartada: criar uma segunda chamada exclusiva para o card. Isso adicionaria latência, estado de carregamento duplicado e nova superfície de autorização sem necessidade.

### 2. O total físico cobre somente três raízes seguras

Um helper reutilizável percorrerá `MEDIA_SOURCE_ROOT`, `MEDIA_DERIVATIVES_ROOT` e `MEDIA_HISTORY_ROOT`, sem seguir links simbólicos e somando somente arquivos regulares. As raízes serão resolvidas pela configuração de mídia já usada pelo servidor. Falha em qualquer raiz torna `available=false`; a API não publicará um total parcial como se fosse completo.

A medição poderá ser memorizada em processo por até 30 segundos para evitar múltiplas varreduras na navegação administrativa. O cache é descartável: reinício da API e expiração natural atualizam o valor, enquanto a contagem do banco é consultada a cada resumo.

Alternativa descartada: somar tamanhos registrados no banco. `PhotoAsset` não guarda bytes e derivados podem ser substituídos; esse cálculo não refletiria a ocupação física real solicitada.

### 3. A interface formata, mas o backend preserva bytes inteiros

O card `Armazenamento de fotos` exibirá `0 MB`, MB abaixo de `1 GiB` e GB a partir de `1 GiB`, usando base binária e arredondamento legível. O detalhe exibirá `N fotos`. Se `available=false`, mostrará `Indisponível` sem ocultar as demais métricas.

Alternativa descartada: retornar texto já formatado pela API. Isso perderia precisão e dificultaria testes, acessibilidade e futuros consumidores.

### 4. O modo sem backup terá sinal e confirmação próprios

O script de manutenção aceitará `--without-backup` somente junto do token literal `DELETE_HOMOLOG_GALLERIES_AND_CLIENTS_WITHOUT_BACKUP`. O pipeline reconhecerá um trailer distinto e explícito, sem alterar o modo atual que cria backup. Antes da mutação, o script imprimirá inventário agregado; depois, repetirá inventário e healthchecks.

O módulo de limpeza continuará truncando apenas as raízes `parent_gallery` e `client` com dependências, removendo sessões/desafios de cliente e entregas operacionais antes do `TRUNCATE`, limpando apenas as três raízes de mídia e o Redis exclusivo. Tabelas administrativas e de preferências não entram nas raízes da exclusão.

Alternativa descartada: executar SQL manual por SSH ou remover o backup do modo padrão. Ambas reduziriam auditabilidade e tornariam uma autorização pontual um comportamento global perigoso.

### 5. A publicação e a limpeza permanecem sequenciadas

A change será integrada por PR e publicada pelo Environment protegido. O deploy saudável ocorre primeiro; a manutenção roda depois usando o trailer autorizado. O estado final será conferido pelo log agregado, pelos healthchecks externos e pela Visão geral administrativa após autenticação humana.

Como a retomada da API pode recriar o container e alterar seu endereço na rede
Compose, a manutenção recarregará também o Nginx exclusivo da Markina depois de
religar os serviços. Além da saúde individual dos containers, a rotina exigirá
resposta bem-sucedida de `127.0.0.1:8080/api/health`; isso impede declarar sucesso
quando o proxy ainda mantém um upstream obsoleto.

## Risks / Trade-offs

- [Varredura física atrasar a Visão geral] → cache curto, uma única projeção e falha isolada sem bloquear o painel.
- [Link simbólico escapar da raiz] → não seguir symlinks nem somar seus alvos.
- [Total parcial parecer correto] → qualquer erro marca a medição inteira como indisponível.
- [Modo sem backup acionado por engano] → ambiente homologado, trailer distinto, flag e token literal independentes, inventário prévio e Environment protegido.
- [Admin/preferências atingidos por CASCADE futuro] → teste PostgreSQL descartável verifica explicitamente as tabelas preservadas antes da execução real.
- [Mídia ser irrecuperável] → consequência aceita e documentada da autorização atual; a operação não promete restauração.

## Migration Plan

1. Adicionar testes inicialmente falhos para métrica, autorização, formatação e modo destrutivo sem backup.
2. Implementar helper de armazenamento, projeção API e card da Visão geral.
3. Estender a manutenção com inventário prévio e modo sem backup estritamente sinalizado; validar em PostgreSQL descartável.
4. Executar testes focados, lint, tipos, build, OpenSpec estrito e revisão do diff.
5. Publicar via PR e Environment protegido usando o trailer específico; acompanhar limpeza, contagens zero, mídia zero, saúde e `FACIAL_PROCESSING_ENABLED=true`.

Rollback de código restaura a versão anterior sem reconstruir os dados apagados. Como a execução foi autorizada sem novo backup, os dados de teste removidos não terão caminho de recuperação fornecido por esta change.
