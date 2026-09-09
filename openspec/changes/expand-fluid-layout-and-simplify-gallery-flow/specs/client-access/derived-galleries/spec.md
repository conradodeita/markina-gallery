## ADDED Requirements

### Requirement: Seleção da cliente com avanço e revisão inequívocos

O sistema SHALL manter na barra flutuante a quantidade, o valor estimado e um CTA com texto visível e nome acessível inequívoco para avançar. Ao abrir a revisão da seleção, a interface SHALL priorizar somente as fotos escolhidas e os dados comerciais aplicáveis, SHALL NOT renderizar a capa editorial da galeria nessa superfície e SHALL preservar a opção de ampliar cada foto. Quando comentários estiverem habilitados, a cliente SHALL poder ler, inserir e remover seus comentários no contexto da respectiva foto ampliada, abaixo da mídia, sem selecionar a foto por um controle separado.

#### Scenario: Cliente seleciona fotos na Galeria pública

- **WHEN** ao menos uma foto integra a seleção
- **THEN** a barra flutuante mostra quantidade, valor e um botão ou link com texto visível `Prosseguir`, contraste suficiente e destino acessível para revisão

#### Scenario: Cliente abre a revisão da seleção

- **WHEN** a cliente aciona `Prosseguir`
- **THEN** a tela apresenta as fotos selecionadas e o resumo comercial sem mostrar a capa da galeria como se ela fosse parte da seleção

#### Scenario: Cliente comenta uma foto ampliada

- **WHEN** comentários estão habilitados e a cliente amplia uma foto selecionada
- **THEN** os comentários daquela foto e o formulário correspondente aparecem abaixo da mídia, sem seletor global de fotos e sem misturar comentários de outro item

#### Scenario: Comentários indisponíveis

- **WHEN** o backend informa que comentários estão desabilitados
- **THEN** o visualizador não apresenta formulário ou lista de comentários e mantém a ampliação e a seleção funcionando normalmente

