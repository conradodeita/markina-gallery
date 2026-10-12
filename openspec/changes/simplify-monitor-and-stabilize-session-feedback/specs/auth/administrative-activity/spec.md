# Spec Delta

## ADDED Requirements

### Requirement: Cor de atividade fundamentada na árvore
A identificação do fotógrafo SHALL ser verde em active e vermelha em inactive, conforme sinais/sessões revalidados já existentes. recent, valid_session e unknown SHALL permanecer neutros. O estado textual MUST permanecer visível; a cor MUST NOT ser a única informação nem transformar sessão válida em atividade ou dado antigo em offline. As cores SHALL ser legíveis nos temas claro/escuro.

#### Scenario: Atividade e ausência de sessão
- **WHEN** a árvore recebe active com evidência atual ou inactive sem sessão válida
- **THEN** a identificação exibe respectivamente verde ou vermelho junto ao estado textual existente

#### Scenario: Sessão ociosa ou dados ausentes
- **WHEN** a árvore recebe recent, valid_session ou unknown
- **THEN** a identificação permanece neutra, com texto que distingue atividade anterior, sessão válida e ausência de evidência
