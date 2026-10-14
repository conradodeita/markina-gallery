# Spec Delta

## ADDED Requirements

### Requirement: Carregamento progressivo das fotos no painel privado

As grades de fotos vinculadas ou carregadas diretamente na galeria privada SHALL adiar imagens fora da área visível, preservando nomes, interações e ações administrativas.

#### Scenario: Fotógrafo abre uma pasta privada extensa

- **WHEN** o fotógrafo abre a página administrativa de uma galeria privada com várias fotos
- **THEN** as imagens dos cards usam carregamento tardio sem alterar a seleção, remoção ou o acesso às prévias protegidas
