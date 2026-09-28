# Spec Delta

## Purpose

Permitir que o fotógrafo opere e confira as pastas exclusivas no Acervo da cliente com poucos passos, feedback claro e prévias administrativas protegidas.

## ADDED Requirements

### Requirement: Processamento visível ao abrir a pasta no Acervo

Ao abrir uma pasta no Acervo da cliente, a configuração e o estado de processamento SHALL aparecer diretamente no conteúdo da pasta, sem exigir a abertura de um segundo painel. A abertura e o fechamento SHALL apenas consultar ou descartar estado de interface, sem salvar configuração nem iniciar processamento. A etapa Imagens SHALL manter seu painel recolhível atual.

#### Scenario: Abrir pasta exclusiva

- **WHEN** o fotógrafo abre a pasta no card do Acervo
- **THEN** vê imediatamente os controles e o progresso do processamento, sem clique adicional ou mutação

#### Scenario: Fechar pasta

- **WHEN** o fotógrafo recolhe a pasta
- **THEN** consultas periódicas do painel cessam e nenhuma configuração é alterada

### Requirement: Upload imediato com progresso confiável

Escolher JPEGs no Acervo SHALL iniciar o envio automaticamente, sem botão adicional. O sistema SHALL mostrar preparo do arquivo, avanço real dos bytes transferidos e contagem de arquivos concluídos no lote, além de estados de espera, conclusão e erro. Retentativas SHALL preservar a identidade estável da foto e não criar ativos duplicados. Um lote com falha SHALL informar quais arquivos não terminaram e permitir nova tentativa explícita; a simples reabertura da pasta SHALL NOT reenviar arquivos.

#### Scenario: Seleção de vários JPEGs

- **WHEN** o fotógrafo confirma arquivos no seletor do dispositivo
- **THEN** o upload começa uma única vez e a interface mostra o avanço do lote até a conclusão

#### Scenario: Espera por capacidade

- **WHEN** o servidor pede espera temporária durante o envio
- **THEN** a interface distingue a espera do progresso de transferência e a retentativa usa o mesmo ativo

#### Scenario: Falha parcial

- **WHEN** um arquivo falha após outros terminarem
- **THEN** a interface identifica a falha e não declara o lote completo; uma nova tentativa não duplica fotos já concluídas

### Requirement: Conferência ampliada de prévias administrativas

As fotos da pasta e as imagens do comparativo antes/depois SHALL poder ser ampliadas em diálogo acessível para conferência no computador e em mobile. A ampliação SHALL usar apenas as prévias administrativas autorizadas, sem expor originais ou retirar controles de autenticação. O diálogo SHALL ter fechamento por botão e Escape e devolver o foco ao acionador.

#### Scenario: Ampliar foto carregada

- **WHEN** o fotógrafo aciona uma miniatura da pasta
- **THEN** vê a prévia permitida ampliada e pode voltar à pasta sem perder seu contexto

#### Scenario: Ampliar comparação

- **WHEN** o fotógrafo aciona a imagem convencional ou ajustada do antes/depois
- **THEN** vê essa mesma versão em tamanho maior, sem solicitar o original
