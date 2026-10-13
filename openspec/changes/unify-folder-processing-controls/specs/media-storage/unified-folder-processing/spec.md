## ADDED Requirements

### Requirement: Visão única com processamento isolado por pasta

A etapa administrativa de imagens SHALL apresentar uma única visão de reconhecimento facial e ajuste automático para a pasta selecionada, aplicável a pastas de conteúdo públicas e privadas. Os parâmetros, o estado e o progresso SHALL ser vinculados à identidade da pasta e SHALL NOT herdar alterações de outra pasta ou da galeria. O gate facial global e seus controles SHALL permanecer inalterados.

#### Scenario: Selecionar uma pasta pública ou privada

- **WHEN** o fotógrafo seleciona uma pasta de conteúdo
- **THEN** a mesma área de processamento mostra o nome, os parâmetros e os progressos facial e de prévias daquela pasta, sem exibir um segundo painel de processamento global duplicado

#### Scenario: Alternar entre pastas

- **WHEN** o fotógrafo seleciona outra pasta pública ou privada
- **THEN** a área única atualiza os dados para a nova pasta, e uma alteração de configuração nessa pasta não altera configurações ou jobs das demais

#### Scenario: Alterar intensidade ou exposição

- **WHEN** o fotógrafo muda intensidade ou exposição
- **THEN** o sistema salva automaticamente os valores e reprocessa somente as fotos elegíveis daquela pasta a partir da fonte limpa, invalidando resultados de gerações anteriores sem ação manual de salvar ou processar a galeria

#### Scenario: Criar pasta sem copiar configuração

- **WHEN** uma nova pasta pública ou privada é criada
- **THEN** ela começa com os defaults existentes para seu tipo, com reconhecimento facial sujeito ao gate global e ajuste automático ativo, sem copiar os valores de outra pasta ou da configuração da galeria

### Requirement: Progresso de upload por pasta sem interrupção visual

Durante o envio de arquivos, a interface SHALL manter visível o progresso real do lote associado à pasta de destino, com posição atual, total e arquivo atual quando disponíveis. Selecionar outra pasta ou atualizar o progresso do processamento SHALL NOT ocultar o lote em andamento, substituir o editor inteiro ou causar piscadas perceptíveis.

#### Scenario: Upload e troca de pasta

- **WHEN** um lote está sendo enviado para uma pasta e o fotógrafo seleciona outra pasta
- **THEN** o estado do lote continua visível e identificado pela pasta de destino até terminar ou falhar

#### Scenario: Atualização periódica de filas durante upload

- **WHEN** as filas facial ou de prévias atualizam durante um lote de upload
- **THEN** os dados de progresso são atualizados sem desmontar o estado do upload nem piscar a tela

#### Scenario: Lote concluído ou falho

- **WHEN** o upload termina ou falha
- **THEN** o resumo daquele lote informa o resultado junto à pasta correspondente e não é apresentado como progresso ativo

### Requirement: Isolamento por fotógrafo com workers compartilhados

Configuração, progresso, jobs e resultados de cada pasta SHALL pertencer ao fotógrafo autorizado. O backend SHALL obter e revalidar o proprietário pelo contexto autenticado, sem aceitar um proprietário imposto pelo navegador. A reutilização do painel e dos workers SHALL NOT compartilhar parâmetros, fontes, marca-d’água ou publicação entre fotógrafos.

#### Scenario: ID de pasta de outro fotógrafo

- **WHEN** um fotógrafo tenta consultar, alterar ou reprocessar uma pasta de outro proprietário
- **THEN** a operação é recusada sem revelar dados da pasta e sem modificar sua configuração ou fila

#### Scenario: Trabalhos de fotógrafos distintos

- **WHEN** a fila compartilhada contém jobs de fotógrafos diferentes
- **THEN** cada execução e publicação utiliza o proprietário e os parâmetros persistidos de seu próprio job/pasta, dentro dos limites operacionais vigentes

### Requirement: Monitoramento coerente com trabalho real

A change SHALL preservar a autorização e o escopo de agregação vigentes do Monitor do sistema. A seleção de uma pasta SHALL apenas consultar estados. Filas SHALL refletir os jobs reais da geração vigente ou seu cancelamento; telemetria SHALL registrar tentativas realmente executadas, incluindo reprocessamentos, sem eventos de trabalho causados somente pela renderização do painel.

#### Scenario: Selecionar outra pasta

- **WHEN** o fotógrafo muda a seleção da pasta sem alterar parâmetros
- **THEN** nenhum job de processamento novo é criado e nenhuma execução é contada no Monitor por essa seleção

#### Scenario: Reprocessar após ajuste

- **WHEN** uma mudança de parâmetro invalida e reenfileira jobs da pasta
- **THEN** o Monitor apresenta os estados reais da fila e registra trabalho somente quando os workers executam as tentativas, sem duplicar fotos ou jobs por causa da interface
