# Spec Delta

## ADDED Requirements

### Requirement: CI distingue candidato protegido da publicação aprovada

O teste técnico de política SHALL validar com o verificador real o snapshot ancestral que introduziu o manifesto exato de runtime, conservando todas as comparações de blobs, e SHALL avaliar separadamente o HEAD atual. Candidato protegido com cofre/migration MUST continuar recusado pelo gate de publicação. Resultado técnico positivo SHALL NOT equivaler a autorização operacional ou atualização dos pins para aceitar o cofre.

#### Scenario: Candidato protegido em desenvolvimento
- **WHEN** o snapshot ancestral do manifesto passa no verificador e o HEAD com migration é classificado protegido e recusado pelo mesmo verificador
- **THEN** o teste técnico comprova as duas condições e informa que a publicação continua bloqueada

#### Scenario: Adulteração ou aprovação indevida
- **WHEN** o manifesto diverge do snapshot, o snapshot positivo inclui migration não admitida ou runtime app sem revisão diverge dos blobs
- **THEN** a validação técnica falha sem ignorar comparações, alterar o verificador ou aprovar a publicação

#### Scenario: Candidato API e web exato
- **WHEN** o HEAD e o snapshot do manifesto são válidos segundo o verificador real
- **THEN** o teste técnico conserva a validação positiva e as aprovações operacionais continuam exigidas
