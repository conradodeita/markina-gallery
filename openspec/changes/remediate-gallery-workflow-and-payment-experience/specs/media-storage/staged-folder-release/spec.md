## REMOVED Requirements

### Requirement: Liberação de lote para galerias privadas

**Reason**: A escolha de galerias privadas na etapa Imagens acopla publicação editorial a clientes específicos e impede o fluxo correto no qual a Galeria pública publica conteúdo e a privada recebe somente fotos selecionadas pela cliente ou escolhidas pelo administrador.

**Migration**: A interface deixa de enviar destinos privados; referências privadas existentes são preservadas. O backend passa a publicar fotos elegíveis na Galeria pública e recusa novos pedidos legados que tentem criar vínculos privados em massa por essa ação.

### Requirement: Nova rodada em pasta distinta

**Reason**: A revisão humana exige acrescentar fotos a uma pasta existente sem recriar a organização visível e sem ocultar a rodada já publicada.

**Migration**: Pastas publicadas passam a aceitar novos uploads administrativos; as fotos novas ficam indisponíveis à cliente até processamento, revisão e publicação incremental.

## ADDED Requirements

### Requirement: Publicação de conteúdo na Galeria pública

O sistema SHALL publicar uma pasta ou suas novas fotos prontas para a Galeria pública de origem sem solicitar destinos privados. A publicação SHALL aplicar o modo de acesso do backend, SHALL NOT criar seleção em nome da cliente e SHALL NOT adicionar referências a galerias privadas sem escolha individual posterior.

#### Scenario: Primeira publicação de pasta

- **WHEN** o fotógrafo publica uma pasta em preparação que possui prévias prontas
- **THEN** as fotos elegíveis tornam-se conteúdo publicado da Galeria pública e a pasta registra o estado publicado

#### Scenario: Galeria privada existente

- **WHEN** a Galeria pública possui clientes ou galerias privadas antes da publicação
- **THEN** o sistema não adiciona automaticamente as novas fotos a essas privadas e preserva suas referências atuais

#### Scenario: Evento coletivo protegido

- **WHEN** uma pasta é publicada em Galeria pública `collective_protected`
- **THEN** o conteúdo permanece acessível somente ao fotógrafo e nenhum endpoint da cliente enumera a grade

### Requirement: Rodada incremental dentro da pasta publicada

O sistema SHALL permitir adicionar JPEGs a uma pasta publicada sem retirar de disponibilidade as fotos anteriores. Cada novo arquivo SHALL permanecer administrativo enquanto estiver em upload, processamento ou revisão e SHALL tornar-se visível somente depois de uma publicação explícita bem-sucedida.

#### Scenario: Upload adicional

- **WHEN** o fotógrafo envia novos JPEGs para uma pasta publicada
- **THEN** as fotos já publicadas permanecem disponíveis e as novas aparecem no painel como preparação não publicada

#### Scenario: Publicação das novas fotos

- **WHEN** o fotógrafo publica a rodada adicional depois de todas as prévias elegíveis estarem prontas
- **THEN** somente os novos itens prontos passam a integrar a Galeria pública, sem duplicar fotos anteriores

#### Scenario: Arquivo falha no processamento

- **WHEN** uma rodada contém foto com processamento falho
- **THEN** o sistema mantém o item falho fora da publicação, informa o erro e permite publicar os demais itens elegíveis sem ocultar o conteúdo anterior
