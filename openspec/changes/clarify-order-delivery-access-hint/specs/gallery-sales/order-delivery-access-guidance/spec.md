# Spec Delta

## Purpose

Orientar a cliente sobre onde acessar o álbum final depois da edição e da liberação das fotos pelo fotógrafo.

## ADDED Requirements

### Requirement: Orientação para acessar o álbum após a edição

O sistema SHALL explicar em Compras como a cliente acessará as fotos quando o álbum ainda estiver indisponível.

#### Scenario: Álbum ainda indisponível
- **WHEN** a cliente consulta um pedido sem álbum liberado
- **THEN** ela vê, junto ao botão desabilitado “Fotos indisponíveis”, a orientação “Após a edição, quando o fotógrafo liberar o álbum, clique em “Fotos disponíveis” para acessá-las.”

#### Scenario: Álbum liberado
- **WHEN** o pedido possui álbum disponível
- **THEN** o botão “Fotos disponíveis” permanece ativo e a orientação de indisponibilidade não é exibida
