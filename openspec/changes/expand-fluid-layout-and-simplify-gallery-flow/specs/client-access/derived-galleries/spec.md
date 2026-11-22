## ADDED Requirements

### Requirement: CTA de avanço da seleção

O sistema SHALL mostrar na barra flutuante a quantidade, o valor estimado e um CTA visível e acessível `Prosseguir` para abrir a revisão.

#### Scenario: Cliente seleciona fotos na Galeria pública

- **WHEN** ao menos uma foto integra a seleção
- **THEN** a barra flutuante mostra quantidade, valor e `Prosseguir` com contraste e destino acessível para revisão

### Requirement: Revisão contém somente fotos escolhidas

A revisão SHALL apresentar somente as fotos selecionadas e dados comerciais aplicáveis, SHALL NOT renderizar a capa editorial como item escolhido e SHALL preservar a ampliação das fotos.

#### Scenario: Cliente abre a revisão da seleção

- **WHEN** a cliente aciona `Prosseguir`
- **THEN** a tela mostra somente as fotos selecionadas e o resumo comercial calculado pelo servidor, sem incluir a capa editorial

### Requirement: Comentários pertencem à foto ampliada

Quando comentários estiverem habilitados, a cliente SHALL poder ler, inserir e remover comentários da foto ativa abaixo da mídia ampliada, sem seletor global nem mistura entre fotos.

#### Scenario: Cliente comenta uma foto ampliada

- **WHEN** comentários estão habilitados e a cliente amplia uma foto selecionada
- **THEN** comentários e formulário daquela foto aparecem abaixo da mídia e não se misturam aos de outra foto

#### Scenario: Comentários indisponíveis

- **WHEN** o backend informa que comentários estão desabilitados
- **THEN** o visualizador não apresenta formulário ou lista de comentários e mantém ampliação e seleção funcionando
