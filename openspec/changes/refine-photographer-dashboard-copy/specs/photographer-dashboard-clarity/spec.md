# Spec Delta

## Purpose

Deixar os estados e ações do painel do fotógrafo claros sem expor detalhes internos de implementação.

## ADDED Requirements

### Requirement: Orientação para saldo insuficiente

Quando a carteira finita impedir novos uploads, a Visão Geral e a tela Créditos SHALL informar “Saldo insuficiente para novos uploads” e oferecer o link “Adquira um pacote →” para a seção de pacotes de créditos. A interface SHALL NOT exibir explicações internas sobre consulta de carteira, reservas por foto ou validação da API.

#### Scenario: Fotógrafo sem saldo tenta enviar conteúdo

- **WHEN** a carteira confirmada informa que novos uploads estão bloqueados por saldo e o fotógrafo consulta a Visão Geral ou Créditos
- **THEN** o painel SHALL apresentar a mensagem de saldo insuficiente
- **AND** SHALL oferecer link para os pacotes de créditos
- **AND** SHALL omitir detalhes técnicos do mecanismo de saldo e reserva

### Requirement: Rótulo da prática de publicação

A seção de orientação para publicação no painel SHALL ser intitulada “Prática de publicação”, preservando as etapas e ações já disponíveis.

#### Scenario: Fotógrafo consulta a orientação de publicação

- **WHEN** o fotógrafo abre o painel administrativo
- **THEN** a seção SHALL aparecer com o título “Prática de publicação”
- **AND** o conteúdo das etapas SHALL permanecer igual
