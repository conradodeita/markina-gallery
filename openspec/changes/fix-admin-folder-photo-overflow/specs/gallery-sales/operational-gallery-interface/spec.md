# Spec Delta

## ADDED Requirements

### Requirement: Cards administrativos de fotos contidos na pasta

A etapa Imagens do editor SHALL manter prévia, nome, estado e ações de cada foto dentro da largura do respectivo card, em celular e desktop. Nomes longos sem espaços SHALL quebrar linha sem ampliar a grade nem ocultar ações. O nome completo SHALL ser preservado, assim como o enquadramento existente da miniatura, a seleção e a ampliação.

#### Scenario: Segunda pasta com nomes extensos
- **WHEN** o fotógrafo abre a segunda pasta com nomes longos sem espaços em uma tela estreita
- **THEN** as imagens e textos permanecem dentro dos cards, sem sobreposição ou rolagem horizontal causada pelas fotos

#### Scenario: Operação dos cards
- **WHEN** o fotógrafo seleciona uma foto ou abre sua prévia após trocar de pasta
- **THEN** os controles continuam acessíveis, a foto correta é selecionada ou ampliada e o layout não provoca requisições de mutação
