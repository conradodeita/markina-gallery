# Spec Delta

## Purpose

Definir como a busca por referência enviada apresenta possibilidades adicionais com política explícita, mantendo correspondências firmes e a autorização da galeria independentes da similaridade.

## ADDED Requirements

### Requirement: Referência enviada possui faixa de possibilidades separada

Consultas SFace com origem persistida `upload` SHALL permitir faixa configurável de possíveis correspondências abaixo do limiar firme, sem reduzir esse limiar. A faixa específica SHALL ser desativável, limitada a 0–1000 e nunca tornar o critério efetivo mais restritivo que o limiar firme ou uma faixa ambígua geral já configurada. Após revisão humana desta proposta, o valor inicial SHALL ser 500 milésimos quando ausente; valor explicitamente vazio SHALL preservar somente a política geral vigente.

#### Scenario: Par positivo abaixo do limite firme
- **WHEN** uma referência enviada supera a faixa de possibilidades mas não o limiar firme
- **THEN** a foto autorizada é apresentada como `ambiguous`, com conferência humana e sem seleção automática

#### Scenario: Correspondência firme
- **WHEN** a similaridade supera o limiar firme vigente
- **THEN** a classificação permanece `matched` e a ordenação firme precede as possibilidades

#### Scenario: Faixa específica desativada
- **WHEN** a configuração específica está explicitamente vazia
- **THEN** a consulta conserva os critérios gerais existentes sem introduzir um valor implícito de possibilidades

### Requirement: Política respeita origem e espaço vetorial

As faixas específicas SHALL ser aplicadas somente pelo servidor a consultas de engine SFace compatível, conforme origem persistida. Consultas por região SHALL usar sua faixa independente e engines experimentais SHALL manter a política geral vigente. Comparação SHALL continuar restrita ao cliente, tenant, galeria, snapshot, versões, fingerprints e disponibilidade autorizados. SHALL NOT expor scores/vetores, conceder acesso ou criar associação de identidade.

#### Scenario: Consulta por toque
- **WHEN** a cliente escolhe uma região já indexada
- **THEN** o comparador usa o vetor persistido e a faixa específica de região aprovada, sem adotar o default de upload

#### Scenario: Engine experimental
- **WHEN** a consulta pertence ao namespace Gemma
- **THEN** o limiar específico SFace não modifica seus critérios nem mistura índices

#### Scenario: Foto inacessível ou índice obsoleto
- **WHEN** uma foto perdeu autorização ou tem fingerprint/versão incompatível
- **THEN** ela não participa do resultado mesmo que sua similaridade ultrapasse qualquer faixa

### Requirement: Toque possui faixa de possibilidades independente

Consultas SFace com origem persistida `indexed_region` SHALL aceitar possibilidades a partir de 600 milésimos por default, sem reduzir o limiar firme. Essa faixa SHALL ser configurável em 0–1000 e desativável por valor explicitamente vazio. O critério efetivo SHALL ser o menor entre limiar firme, faixa geral e faixa específica aplicável.

#### Scenario: Toque encontra similaridade intermediária
- **WHEN** uma foto autorizada possui similaridade entre 600 e o limiar firme 750
- **THEN** ela aparece como `ambiguous`, sem afirmar identidade nem selecionar automaticamente

#### Scenario: Política de toque não altera o upload
- **WHEN** uma referência enviada tem similaridade 550 e as duas faixas específicas estão nos defaults
- **THEN** ela pode aparecer como possibilidade pelo limite 500; o limite 600 por toque não a restringe

#### Scenario: Limite firme configurado abaixo da faixa específica
- **WHEN** o limiar firme explicitamente configurado é menor que a faixa da origem
- **THEN** o critério efetivo não exclui correspondências firmes válidas
