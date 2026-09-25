# Spec Delta

## Purpose

Reduzir a densidade visual da central de Notificações preservando integralmente a configuração e o salvamento de cada evento existente.

## ADDED Requirements

### Requirement: Cards inicialmente recolhidos e independentes

A central SHALL apresentar cada card inicialmente recolhido, mostrando somente destinatário, título existente e seta. O cabeçalho SHALL permitir expandir e recolher por clique ou teclado, com foco visível e estado acessível, independentemente dos outros cards.

#### Scenario: Carregamento e alternância
- **WHEN** o fotógrafo abre a central e aciona o cabeçalho de um evento
- **THEN** somente esse card expande todas as configurações existentes; novo acionamento o recolhe e os demais mantêm seu estado

### Requirement: Alternância sem efeitos de negócio

Abrir ou recolher SHALL preservar rascunhos, canais, prévias, validações e resultados do salvamento, sem chamadas adicionais à API nem persistência do estado de abertura. A ação explícita de salvar SHALL manter o contrato existente.

#### Scenario: Rascunho preservado
- **WHEN** o fotógrafo edita texto ou canal, recolhe e reabre
- **THEN** os valores editados continuam disponíveis e nenhuma requisição adicional foi enviada

#### Scenario: Salvamento explícito e erro
- **WHEN** o fotógrafo salva um card expandido
- **THEN** apenas o evento escolhido é enviado com a versão e campos existentes; erro preserva o rascunho e a mensagem, inclusive após recolher e reabrir
