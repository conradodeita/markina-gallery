## ADDED Requirements

### Requirement: Prova conjunta de backup e recuperação isolada

O ensaio SHALL usar dados sintéticos e verificar recuperação global, seleção dos dados de um fotógrafo e solicitação de recuperação de mídia fria pelo fluxo autenticado do produto. MUST comprovar isolamento entre fotógrafos e verificação integral antes da disponibilização da pasta.

#### Scenario: Recuperação global em ambiente descartável

- **WHEN** a cópia cifrada é recuperada com a chave em custódia separada
- **THEN** a prova SHALL restaurar os dados sintéticos em um PostgreSQL isolado e registrar tempos e integridade

#### Scenario: Recuperação de um fotógrafo e pasta fria

- **WHEN** um fotógrafo autorizado solicita recuperar uma pasta própria
- **THEN** o fluxo SHALL selecionar os objetos no catálogo por tenant, validar tamanho e checksum e disponibilizar a pasta no destino privado
- **AND** uma solicitação para pasta de outro fotógrafo ou prova de integridade divergente MUST impedir a entrega e o débito
