## ADDED Requirements

### Requirement: Prova global e recuperação seletiva isolada

O ensaio SHALL usar dados sintéticos para recuperar um backup global e selecionar os registros de um fotógrafo em banco isolado. MUST comprovar ausência de dados cruzados entre fotógrafos.

#### Scenario: Recuperação global em ambiente descartável

- **WHEN** a cópia cifrada é recuperada com a chave em custódia separada
- **THEN** a prova SHALL restaurar os dados sintéticos em um PostgreSQL isolado e registrar tempos e integridade

### Requirement: Ferramentas comuns mantêm domínios de armazenamento separados

O mesmo conjunto de ferramentas SHALL ser avaliado no backup global e na recuperação de mídia fria. Credenciais, raízes, namespaces e políticas de retenção SHALL permanecer separados; ferramentas e filtros de caminho MUST NOT substituir a autorização por tenant no servidor.

#### Scenario: Uma ferramenta comum atende dados de escopos distintos

- **WHEN** o piloto usa ferramentas comuns para banco global e pasta de mídia
- **THEN** cada fluxo mantém raiz, identidade e política próprias e o servidor valida tenant e catálogo antes de acessar a pasta

### Requirement: Recuperação fria preserva prazos e créditos existentes

A prova de mídia SHALL usar o fluxo autenticado existente e preservar prazos, créditos, idempotência, reconciliação e ausência de expurgo automático descritos em `add-gallery-media-archive`. MUST NOT criar fila, catálogo, UI ou cobrança paralelos.

#### Scenario: Recuperação de um fotógrafo e pasta fria

- **WHEN** um fotógrafo autorizado solicita recuperar uma pasta própria
- **THEN** o fluxo SHALL selecionar os objetos no catálogo por tenant, validar tamanho e checksum e disponibilizar a pasta no destino privado
- **AND** uma solicitação para pasta de outro fotógrafo ou prova de integridade divergente MUST impedir a entrega e o débito

#### Scenario: Prazo e créditos continuam ligados à recuperação verificada

- **WHEN** a prova executa a solicitação autenticada de recuperação fria de uma pasta
- **THEN** exercita a janela de elegibilidade de 30 dias, uma duração permitida de 7, 14 ou 30 dias e a taxa configurável por pasta/ciclo
- **AND** reserva uma única vez, debita somente após readback e checksum integrais, libera em falha comprovada e conserva a reserva para reconciliação se o resultado for incerto
- **AND** mantém a isenção do proprietário, o início do novo prazo após recuperação íntegra e a proibição de expurgo automático
