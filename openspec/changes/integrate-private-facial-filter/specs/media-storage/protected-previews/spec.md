## ADDED Requirements

### Requirement: Prévia facial limitada ao conjunto já autorizado

O sistema SHALL montar candidatos faciais somente com fotos cuja prévia de cliente já esteja pronta e autorizada para aquela sessão na Galeria pública e pertença ao snapshot congelado da consulta. O endpoint de prévia SHALL repetir a autorização normal por requisição e SHALL NOT aceitar resultado facial como capacidade de acesso.

#### Scenario: Referência aponta para foto não autorizada

- **WHEN** um resultado vencido, adulterado ou inconsistente contém foto fora do conjunto atualmente autorizado
- **THEN** o backend omite a candidata e nega a prévia sem revelar existência, caminho ou metadados

### Requirement: Separação entre mídia e material biométrico

Originais, prévias, referências temporárias e embeddings SHALL usar ciclos e autorizações separados. O navegador SHALL receber somente a prévia protegida, IDs opacos, banda pública `best|other`, posição e progresso agregado necessários ao filtro; SHALL NOT receber referência armazenada, vetor, indicadores técnicos brutos, similaridade, landmarks, caixa facial, caminho interno ou modelo.

#### Scenario: Cliente consulta resultado

- **WHEN** a cliente carrega ou atualiza o bloco de possíveis fotos
- **THEN** a resposta contém apenas referências autorizadas, ordem e estado de expiração, sem artefato biométrico

### Requirement: Exclusão do índice acompanha a origem

Excluir ou retirar uma foto da finalidade facial SHALL eliminar todos os seus embeddings e candidatos temporários, mesmo quando mídia comercial histórica precisar permanecer. Reprocessar a prévia SHALL reindexar somente se a política facial continuar ativa e válida.

#### Scenario: Galeria pública excluída com privada preservada

- **WHEN** a origem pública é excluída e fotos selecionadas permanecem em privada ou histórico
- **THEN** o índice facial e os resultados da origem são eliminados sem apagar a mídia e os snapshots que devam sobreviver comercialmente
