# Spec Delta

## ADDED Requirements

### Requirement: Release API/web valida manifestos Compose vigentes

Os helpers de inventário e release API/web SHALL NOT exigir um overlay Compose removido por uma mudança de aposentadoria integrada. SHALL continuar conferindo os demais arquivos e a identidade Compose dos containers ativos. Quando um manifesto exigido estiver ausente, a falha SHALL identificar o caminho e SHALL ocorrer antes de build, troca de imagem ou recriação.

#### Scenario: Overlay RAW aposentado

- **WHEN** um helper API/web é executado após a aposentadoria do overlay RAW e o arquivo `docker/docker-compose.raw-development.yml` não existe no checkout
- **THEN** o helper API/web não o inclui na lista de manifestos nem nos labels esperados e prossegue com a conferência dos manifestos vigentes

#### Scenario: Outro manifesto ausente

- **WHEN** qualquer outro manifesto exigido pelo inventário não existe
- **THEN** o preflight falha antes de mutação e informa qual caminho está ausente
