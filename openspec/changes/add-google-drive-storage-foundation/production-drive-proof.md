# Ensaio do Google Drive em produção — 17/11/2026

## Quota confirmada

- A API publicada no Oracle, release `bfe511f`, usou a conexão ativa do proprietário com escopo `drive.file`. A seleção da conexão PostgreSQL foi somente leitura. O helper de quota do aplicativo renovou o acesso em memória e consultou `about.storageQuota(limit,usage)` no Google.
- Quota informada de 109951162777600 bytes (100 TiB), com 10658056609008 bytes em uso (9,69 TiB). A diferença observada foi 90,31 TiB. É uma leitura pontual da conta conectada. Ela não certifica uma pasta, um drive compartilhado ou a identidade dedicada do futuro job.
- A checagem não alterou o registro de quota do console e não retornou credenciais.

## Upload, leitura e limpeza

O proprietário indicou `Meu Drive / Oracle-Production-Backups / Pick-your-Pic Tenants`. A busca apenas pelo nome da pasta raiz, com a credencial da aplicação e escopo `drive.file`, retornou zero correspondências visíveis. Com o link direto fornecido pelo proprietário, a API respondeu HTTP 404 ao pedido de metadados do ID exato, com suporte a drives compartilhados habilitado na consulta. A resposta demonstra que a conexão do app não conseguiu acessar essa pasta e não determina se a pasta existe na conta. O app publicado ainda não oferece um seletor Google para autorizar uma pasta preexistente.

O roteiro prevê um arquivo textual sintético com identificador exclusivo, envio retomável pelo helper da aplicação, conferência de destino, permissões, tamanho e MD5, leitura do conteúdo e verificação de SHA-256. A limpeza elimina exclusivamente os objetos criados na execução depois de conferir seus IDs e marcadores e verifica a ausência. A validação usa a conexão do proprietário. Criar um tenant da aplicação não é necessário para esse ensaio de transporte.

O ensaio `9ba7955ee7654b5888b15d05399e40e5` parou no acesso à pasta, antes do upload. Nenhum objeto, tenant ou arquivo temporário foi criado na produção ou no Drive e a pasta não foi alterada. Uma pasta privada temporária criada pelo app pode provar o transporte após escolha do proprietário. Ela não comprova as permissões do destino definitivo nem da identidade dedicada.

## Ensaio com pasta temporária concluído

- O proprietário escolheu e autorizou uma pasta privada temporária no Meu Drive. Ensaio `0d2a0c118ca54699ad3029ef51a3b82c`, com a conexão do proprietário já ativa e a API `bfe511f` no Oracle. A pasta criada pelo app apresentou somente permissão de proprietário, sem acesso público.
- O helper real fez upload retomável de um texto sintético de 101 bytes. ID reservado, pasta pai, tamanho e MD5 conferiram na confirmação e na releitura de metadados. O download íntegro conferiu byte a byte e teve SHA-256 `5041cea2416de7bba2ca165584ec4e5d91bd8112622883bdf69c2b92657e3588`.
- Os únicos objetos criados foram o arquivo sintético e a pasta temporária. O operador conferiu os IDs e marcadores, excluiu o arquivo, confirmou a pasta vazia e privada e excluiu a pasta. Consultas pelos dois IDs depois da exclusão retornaram HTTP 404. O conteúdo e as credenciais ficaram em memória. O recibo tem somente metadata técnica.
- A prova confirma quota, escrita, leitura e limpeza na pasta temporária. A pasta definitiva indicada ainda não está acessível a essa conexão. A escolha e autorização do destino da rotina, a identidade dedicada e o ensaio de backup global e recuperação continuam pendentes. A pasta indicada, os demais arquivos e os registros de auditoria foram preservados.

## Destino da rotina verificado

- Em 17/11/2026, o proprietário escolheu a mesma conta Workspace já conectada para a rotina global e autorizou criar `Pick-your-Pic Tenants`. Às 17h16 BRT, a API `bfe511f` criou uma nova pasta na raiz do Meu Drive com um marcador do app para backup do banco. A pasta homônima dentro de `Oracle-Production-Backups` permaneceu fora da operação.
- O Google confirmou que a pasta está na raiz do Meu Drive, pertence ao proprietário, está autorizada para o app com `drive.file` e pode receber arquivos. A lista de permissões apresentou apenas a do proprietário e a consulta de filhos visíveis ao app retornou zero.
- A pasta é permanente e foi criada vazia. Ainda faltam o vínculo ao caller de produção, a chave de recuperação operacional e a prova recorrente de backup nesse destino.

[Operação planejada do backup](../../../docs/saas-evolution/operacao-backup.md).
