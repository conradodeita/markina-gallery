# Spec Delta

## Purpose

Definir o desenvolvimento privado e temporário de RAWs enviados pelo fotógrafo, com motores selecionáveis, versões identificáveis e descarte dos arquivos-fonte após a criação segura dos derivados.

## ADDED Requirements

### Requirement: Compatibilidade por motor e formato

O sistema SHALL consultar a capacidade do motor selecionado e SHALL aceitar os formatos RAW suportados por esse motor, sem restringir a instalação a uma única marca ou corpo de câmera. Sony ARW é o primeiro caso de compatibilidade a validar para o proprietário atual, não um limite global do produto. Extensão/MIME não comprovam que a imagem pôde ser decodificada.

#### Scenario: Formato aceito pelo motor selecionado
- **WHEN** o fotógrafo envia um arquivo cujo formato e dados de câmera são decodificados pelo motor selecionado
- **THEN** o sistema processa o arquivo e registra formato, câmera e versão do motor na proveniência operacional

#### Scenario: Outro fabricante ou corpo compatível
- **WHEN** um fotógrafo usa outro fabricante/corpo com formato declarado e efetivamente decodificado pelo motor
- **THEN** o sistema admite o arquivo sem exigir aprovação global de um único corpo Sony

#### Scenario: Motor não decodifica arquivo
- **WHEN** o arquivo tem uma extensão conhecida, mas a versão do motor não reconhece sua variante/câmera ou falha ao decodificá-la
- **THEN** o sistema marca falha individual, descarta temporários e não publica derivados parciais

### Requirement: Limites de processamento RAW

O sistema SHALL limitar cada upload RAW a 256 MiB, 64 fontes simultâneas, 2 GB totais, saída de até 40 megapixels, timeout de conversão de 15 minutos, retenção temporária máxima de 24 horas e duas tentativas.

#### Scenario: Limite excedido
- **WHEN** upload ou conversão excede limite de bytes, quota, pixels ou tempo
- **THEN** a fonte não é publicada, temporários são limpos e o estado informa falha ou reenvio exigido

### Requirement: Transporte de arquivos RAW grandes

A rota autenticada de upload de fonte e seus proxies SHALL transportar o limite funcional de 256 MiB. O limite adicional de transporte SHALL se aplicar somente à rota de fontes; limites funcionais de JPEG e demais endpoints permanecem inalterados. O navegador SHALL calcular a chave de retomada de RAW por blocos para não ler o arquivo inteiro numa única alocação de memória.

#### Scenario: RAW acima de 47 MiB
- **WHEN** o fotógrafo envia um RAW maior que 47 MiB e menor ou igual a 256 MiB
- **THEN** o proxy e a API aceitam o tamanho para validação e staging, respeitadas as quotas e a assinatura do formato

### Requirement: Proveniência operacional sem fonte

O registro SHALL conter `tenant_id`, fingerprint, bytes, formato, fabricante/modelo da câmera quando lidos, motor/versão, perfil, dimensões de saída, status e expiração, sem guardar bytes RAW nem nomes de arquivo em campos de caminho. Configuração do motor e consulta de versão SHALL ser isoladas por tenant. Rotas e workers SHALL restringir leitura e alteração dos jobs ao tenant proprietário da foto.

#### Scenario: Registro de proveniência
- **WHEN** um arquivo RAW compatível é admitido ou desenvolvido
- **THEN** o sistema registra seus metadados operacionais sem reter os bytes nem o nome original como caminho

### Requirement: Transições duráveis e idempotentes

O sistema SHALL rejeitar transições de estado inválidas e SHALL exigir novo envio explícito para reabrir um resultado pronto.

#### Scenario: Transição de status
- **WHEN** uma operação tenta saltar uma etapa ou reabrir resultado pronto sem um novo envio explícito
- **THEN** o sistema rejeita a transição e mantém a proveniência do trabalho atual

### Requirement: Desenvolvimento RAW opcional e isolado

O sistema SHALL oferecer ao administrador a ativação do módulo de desenvolvimento RAW e a seleção do motor disponível. O módulo SHALL permanecer desligado por padrão, e a seleção SHALL NOT alterar o processamento existente de JPEGs.

#### Scenario: RAW enviado com módulo ativo
- **WHEN** o fotógrafo envia um RAW compatível para uma capa ou pasta de conteúdo com o módulo ativo
- **THEN** o sistema desenvolve uma imagem de trabalho usando o motor selecionado e encaminha essa imagem ao pipeline de prévias vigente

#### Scenario: RAW enviado com módulo desligado
- **WHEN** o fotógrafo tenta enviar um RAW enquanto o módulo está desligado
- **THEN** o sistema recusa o arquivo com orientação para ativar o módulo ou enviar JPEG, sem alterar a galeria

#### Scenario: JPEG após ativar o módulo
- **WHEN** o fotógrafo envia JPEG pelo fluxo atual enquanto o módulo RAW está ativo
- **THEN** o sistema mantém o processamento JPEG vigente, sem converter nem reprocessar o arquivo por LightCraft

### Requirement: Compatibilidade e falha de desenvolvimento

O sistema SHALL validar o formato e a câmera suportados pelo motor selecionado e SHALL impedir a publicação de um ativo RAW sem desenvolvimento e derivados íntegros.

#### Scenario: Formato ou câmera sem suporte
- **WHEN** o arquivo RAW não puder ser decodificado pelo motor selecionado
- **THEN** o lote informa falha específica para esse arquivo, não libera prévia parcial e preserva o restante da operação

#### Scenario: Falha recuperável
- **WHEN** o desenvolvimento falha por motivo recuperável
- **THEN** o sistema permite retentativa limitada dentro da retenção temporária e informa quando será necessário reenviar o arquivo

### Requirement: Fontes temporárias sem retenção permanente

O sistema SHALL manter RAW enviado e imagem de trabalho em armazenamento temporário delimitado, sem incluí-los em arquivo frio, cópia do Google Drive, entrega ou backup de mídia, e SHALL removê-los ao concluir o processamento ou expirar a retentativa.

#### Scenario: Processamento concluído
- **WHEN** o motor valida um JPEG de trabalho e depois o índice elegível e os derivados necessários terminam
- **THEN** o sistema remove o RAW imediatamente após validar/gravar o JPEG e remove o JPEG de trabalho ao concluir seu lifecycle, conservando somente derivados e metadados operacionais permitidos

#### Scenario: Retenção temporária expirada
- **WHEN** o processamento não pode ser concluído antes do limite configurado
- **THEN** o sistema remove os arquivos temporários, registra estado que exige novo envio e não indica a foto como pronta

### Requirement: Seleção e versão do motor rastreáveis

O sistema SHALL registrar motor e versão usados em cada desenvolvimento, permitir ao administrador selecionar por tenant um motor instalado para novos envios RAW e informar a versão instalada e o lançamento estável mais recente conhecido sem substituir o executável automaticamente.

#### Scenario: Nova versão disponível
- **WHEN** uma consulta válida informa que há lançamento mais recente que a versão instalada
- **THEN** o painel administrativo informa ambas as versões e oferece as notas do lançamento, mantendo o motor instalado em uso até atualização controlada

#### Scenario: Serviço de versões indisponível
- **WHEN** o serviço de lançamentos está inacessível
- **THEN** o painel preserva a versão instalada e indica que a informação de atualização não pôde ser atualizada

#### Scenario: Troca de motor
- **WHEN** o proprietário seleciona outro motor já instalado
- **THEN** novos envios RAW usam a seleção e resultados anteriores permanecem identificados por motor/versão, sem reprocessamento automático

#### Scenario: Reprocessamento após descarte da fonte
- **WHEN** o proprietário deseja desenvolver novamente uma foto cuja fonte RAW já foi removida
- **THEN** o sistema informa que é necessário reenviar o RAW e preserva os derivados existentes até a nova geração estar pronta

### Requirement: Comparação antes da recomendação

O sistema SHALL permitir avaliar motores em lote autorizado e manter o processamento JPEG atual como padrão até compatibilidade, qualidade visual, desempenho e capacidade no ambiente alvo serem aceitos pelo proprietário.

#### Scenario: Avaliação pendente
- **WHEN** faltam evidências para um ou mais gates de avaliação
- **THEN** LightCraft permanece opcional e não substitui silenciosamente o motor padrão nem o fluxo JPEG

### Requirement: Isolamento do desenvolvimento RAW por tenant

Configurações e jobs RAW SHALL pertencer a um tenant ativo. Um job SHALL referenciar uma foto do mesmo tenant por integridade relacional composta. Endpoints administrativos SHALL derivar o tenant da sessão e SHALL NOT aceitar tenant externo como autoridade. Workers SHALL validar a propriedade persistida antes do processamento e da publicação.

#### Scenario: Upload e consulta no tenant proprietário
- **WHEN** um administrador autenticado envia um RAW associado a uma foto pertencente ao seu tenant
- **THEN** configuração, job e estado persistido usam o mesmo `tenant_id`

#### Scenario: Tenant diferente ou inativo
- **WHEN** uma requisição tenta acessar uma foto/job de outro tenant ou um worker encontra propriedade inconsistente
- **THEN** a API responde sem revelar o recurso e o worker não processa nem publica o arquivo
