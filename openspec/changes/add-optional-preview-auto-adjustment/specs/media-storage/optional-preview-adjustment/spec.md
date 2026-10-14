## Purpose

Melhorar opcionalmente a apresentação das prévias de venda, preservando arquivos, acesso privado e retorno imediato ao tratamento convencional.

## ADDED Requirements

### Requirement: Ativação reversível

O módulo SHALL iniciar desligado. Somente o administrador SHALL alterar sua configuração global. Desligar SHALL impedir novos agendamentos e fazer próximas requisições de prévia usarem a versão convencional, inclusive quando houver resultados prontos ou trabalhos em andamento. A interface já aberta SHALL refletir a mudança ao recarregar suas imagens.

#### Scenario: Desligamento durante processamento
- **WHEN** o administrador desliga o módulo com trabalho em andamento
- **THEN** o resultado desse trabalho não passa a ser usado pelo cliente e o original, a prévia convencional e a entrada facial permanecem intactos

### Requirement: Tratamento independente e recuperável

Com o módulo habilitado, fotos novas de conteúdo com prévias prontas SHALL receber trabalho durável independente da presença de rostos. Falha, ausência do motor ou interrupção SHALL manter seleção, compra e indexação disponíveis com a prévia convencional. Trabalhos SHALL ser idempotentes, limitados e recuperáveis após abandono; fotos existentes SHALL ser agendadas somente por ação administrativa explícita e paginada.

#### Scenario: Falha do motor
- **WHEN** o motor falha ou excede seu tempo limite
- **THEN** o painel informa a falha e a cliente continua recebendo a prévia convencional

#### Scenario: Foto sem rosto e repetição
- **WHEN** a mesma foto sem rosto é agendada duas vezes sem mudança de configuração ou fonte
- **THEN** existe somente um resultado vigente e nenhum trabalho facial adicional é criado

### Requirement: Proteção e isolamento dos resultados

O ajuste SHALL modificar somente cor e tonalidade de uma cópia de prévia e aplicar marca-d'água/grade após o tratamento. O resultado SHALL respeitar dimensões, remoção de EXIF/GPS e autorização vigentes. Alterar proteção ou regenerar a fonte SHALL tornar resultados anteriores inelegíveis. Falta do arquivo tratado SHALL retornar a prévia convencional. Histórico comercial arquivado e capas SHALL continuar usando o fluxo convencional.

#### Scenario: Prévia autorizada e fallback
- **WHEN** uma cliente autorizada solicita foto com resultado vigente
- **THEN** recebe a versão ajustada protegida; sem resultado vigente recebe a convencional e nunca recebe o original ou uma cópia limpa

#### Scenario: Mudança da marca-d'água
- **WHEN** a configuração de proteção muda
- **THEN** nenhum resultado com proteção antiga é selecionado pelo módulo

### Requirement: Operação administrativa simples

O administrador SHALL visualizar ativação e contagem de trabalhos por estado, solicitar processamento por galeria e comparar a prévia convencional protegida com a tratada. Os controles SHALL funcionar em mobile e desktop sem acrescentar etapas ou mensagens técnicas ao cliente.

#### Scenario: Comparação
- **WHEN** o fotógrafo informa uma foto da galeria em avaliação com ajuste concluído
- **THEN** pode ver antes/depois preservando proporção, proteção e autenticação

### Requirement: Higienização delimitada

O módulo SHALL possuir procedimento de inventário e limpeza de seus resultados/trabalhos, permitido somente desligado e com worker parado. Exclusões de fotos SHALL incluir os arquivos e registros exclusivos do módulo. A limpeza SHALL preservar prévias convencionais, originais, pedidos, seleções, favoritos e índice facial.

#### Scenario: Remoção do experimento
- **WHEN** o operador executa a limpeza explícita após desligar e parar o worker
- **THEN** somente arquivos e registros identificados como pertencentes ao módulo são removidos e o comportamento convencional permanece disponível
