# Spec Delta

> **Registro histórico — fluxo aposentado em 25/11/2026.** Os requisitos abaixo descrevem o diagnóstico do runtime global legado removido pela PR #436 (`eff4d504`); não são contrato para reimplementação. A retirada remanescente está em `retire-platform-backup-runtime`, e a nova prova está em `prove-open-source-backup-and-recovery`. Esta delta permanece como evidência; specs principais compartilhadas continuam preservadas.

## ADDED Requirements

### Requirement: Comparação agregada com o Compose vigente
O diagnóstico protegido SHALL comparar, para cada papel fixo da Markina Gallery, os registros identificados pelos labels Compose com os registros enumerados pela configuração Compose vigente. A resposta MUST conter somente contagens agregadas e MUST NOT aprovar, escolher ou alterar a identidade de qualquer container.

#### Scenario: Registros correspondem ou divergem
- **WHEN** os conjuntos de registros do Docker e do Compose vigente são consultados para `api`, `web` e `db`
- **THEN** o diagnóstico informa por papel somente contagens de registros de cada fonte, correspondências e diferenças entre as fontes
- **AND** IDs, nomes, labels, caminhos, valores de configuração e saídas brutas MUST NOT aparecer na resposta ou nos logs

#### Scenario: Consulta parcial, inválida ou acima do limite
- **WHEN** uma fonte falha, retorna um registro inválido ou excede o limite fixo de registros
- **THEN** o diagnóstico descarta todas as contagens e retorna somente um código estático allowlisted
- **AND** nenhuma fingerprint ou precondição aprovada é emitida

#### Scenario: Comparação não altera a guarda de identidade
- **WHEN** a comparação encontra zero ou múltiplos registros para um papel
- **THEN** o inventário normal continua recusando esse papel até validar exatamente um ID completo e seus labels Compose
- **AND** as contagens não autorizam seleção, vínculo, ensaio, backup, remoção ou qualquer operação mutável
