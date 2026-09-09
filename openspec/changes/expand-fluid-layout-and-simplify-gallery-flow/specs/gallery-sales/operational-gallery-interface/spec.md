## ADDED Requirements

### Requirement: Capa dedicada sem varredura do acervo

Na etapa 03, o sistema SHALL permitir definir ou substituir a capa exclusivamente pelo envio de um JPEG do dispositivo para a pasta técnica de capa. O contrato de Detalhes SHALL NOT listar fotos das pastas de conteúdo como opções de capa e o upload aceito SHALL tornar a nova imagem a capa vigente, apresentando processamento e prévia protegida sem exigir uma segunda escolha. Capa preexistente de conteúdo SHALL permanecer compatível para leitura até ser substituída, sem voltar a aparecer como catálogo de opções. Tipografia, cor, tamanho e posição do título SHALL continuar configuráveis e independentes do upload.

#### Scenario: Galeria com muitas fotos de conteúdo

- **WHEN** o fotógrafo abre a etapa 03 de uma galeria com milhares de fotos nas pastas
- **THEN** a etapa carrega somente a configuração e o estado da capa vigente, sem consultar ou renderizar o acervo como lista de candidatas

#### Scenario: Fotógrafo envia nova capa

- **WHEN** um JPEG válido é enviado pelo dispositivo na etapa 03
- **THEN** o sistema registra a intenção de capa, processa o derivado protegido e apresenta essa imagem como capa vigente assim que estiver pronta, sem exigir seleção adicional

#### Scenario: Capa ainda em processamento

- **WHEN** a nova capa foi aceita e seu derivado ainda não está pronto
- **THEN** a etapa mostra estado de processamento, mantém os controles tipográficos utilizáveis e atualiza a prévia quando o backend confirmar conclusão

#### Scenario: Galeria com capa legada de conteúdo

- **WHEN** a galeria já aponta para uma foto de conteúdo como capa antes desta mudança
- **THEN** a apresentação continua usando essa capa até novo upload, mas a etapa 03 não lista outras fotos de conteúdo nem oferece novamente essa origem

### Requirement: Imagens sem ação duplicada de capa

Na etapa 04, o sistema SHALL apresentar pastas, uploads, prévias, ampliação, seleção administrativa, exclusão e estados de processamento/publicação, mas SHALL NOT apresentar `Usar como capa`, `Capa atual` ou ação equivalente em cada foto de conteúdo. A gestão de capa SHALL existir somente na etapa 03.

#### Scenario: Fotógrafo abre uma pasta na etapa 04

- **WHEN** as prévias das fotos correspondentes são exibidas
- **THEN** cada foto mantém suas ações de mídia permitidas e nenhuma delas oferece definição ou indicação operacional de capa

