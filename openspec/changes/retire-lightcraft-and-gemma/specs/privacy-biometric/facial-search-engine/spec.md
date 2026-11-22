# Spec Delta

## Purpose

Definir o motor facial único disponível no produto e preservar a separação entre o índice SFace vigente e registros experimentais históricos.

## ADDED Requirements

### Requirement: Busca facial usa somente YuNet e SFace

O produto SHALL servir buscas faciais somente pelo detector YuNet e pelo reconhecedor SFace versionado. Nenhuma configuração administrativa ou parâmetro de cliente SHALL permitir selecionar outro motor.

#### Scenario: Consulta facial de cliente
- **WHEN** uma cliente autorizada envia uma referência ou toca em uma região facial indexada
- **THEN** a busca usa exclusivamente o namespace SFace e preserva as verificações atuais de consentimento, autorização, retenção e escopo da galeria

#### Scenario: Configuração legada aponta para motor aposentado
- **WHEN** a configuração histórica ou um registro de busca menciona Gemma
- **THEN** o produto não agenda trabalho Gemma nem usa esse valor para responder a clientes; novas consultas usam SFace

### Requirement: Histórico experimental permanece separado e preservado

O sistema SHALL manter registros históricos de motores experimentais separados do índice SFace e SHALL NOT apagar embeddings, jobs ou consultas históricos como efeito implícito da remoção do seletor.

#### Scenario: Busca SFace com vetores experimentais históricos
- **WHEN** uma galeria contém vetores de mais de um modelo
- **THEN** a consulta compara somente vetores SFace compatíveis com a versão, dimensão e política atuais

#### Scenario: Dados experimentais encontrados na operação
- **WHEN** um inventário identifica embeddings ou jobs Gemma existentes
- **THEN** a desativação do runtime preserva esses registros até procedimento explícito e aprovado de retenção ou exclusão
