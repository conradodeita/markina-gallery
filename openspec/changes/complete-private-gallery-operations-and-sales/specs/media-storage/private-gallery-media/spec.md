## Purpose

Definir a propriedade, o upload e o processamento de JPEGs enviados pelo fotógrafo exclusivamente para uma galeria privada, sem ampliar sua visibilidade para outros acervos.

## ADDED Requirements

### Requirement: Upload privado exclusivo

O sistema SHALL permitir ao fotógrafo autenticado criar pastas em uma galeria privada e carregar JPEGs do próprio dispositivo. Cada arquivo SHALL pertencer exclusivamente à galeria privada de destino e SHALL NOT aparecer em Galeria pública ou ser reutilizável em outra galeria privada.

#### Scenario: Fotógrafo carrega JPEGs na privada

- **WHEN** o fotógrafo seleciona uma pasta privada válida e envia JPEGs aceitos
- **THEN** o sistema associa cada arquivo somente àquela galeria privada e inicia seu processamento sem criar referência pública

#### Scenario: Tentativa de reutilização cruzada

- **WHEN** uma operação tenta vincular a outra galeria uma foto pertencente a uma privada
- **THEN** o backend recusa a operação sem duplicar arquivo, derivado ou autorização

### Requirement: Pipeline completo e escopo facial isolado

O sistema SHALL processar fotos privadas pelo pipeline vigente de validação JPEG, prévia limpa, prévia protegida, remoção de metadados e indexação facial quando habilitada. Métricas e índices faciais SHALL permanecer no escopo da privada e SHALL NOT produzir candidatas em busca de uma Galeria pública.

#### Scenario: Processamento privado concluído

- **WHEN** os derivados de uma foto privada ficam prontos
- **THEN** o fotógrafo vê o progresso e as métricas daquela privada e seus membros autorizados recebem somente a prévia protegida

#### Scenario: Busca pública no mesmo evento

- **WHEN** uma busca facial é executada na Galeria pública relacionada ao mesmo evento
- **THEN** nenhuma foto exclusiva da privada participa do snapshot ou dos resultados públicos

### Requirement: Pastas e acesso compartilhado da privada

O sistema SHALL organizar as fotos exclusivas em pastas próprias da galeria privada. Todos os membros ativos da mesma privada SHALL visualizar o mesmo acervo disponível, mantendo seleções, pedidos e pagamentos individuais.

#### Scenario: Privada com mais de um membro

- **WHEN** uma pasta privada processada é disponibilizada e a privada possui vários membros ativos
- **THEN** todos veem as mesmas fotos protegidas, mas a ação de um membro não altera a seleção ou o pedido de outro

### Requirement: Lifecycle sem dependência da origem pública

O sistema SHALL permitir operar e excluir referências privadas próprias sem depender da existência ou do estado da Galeria pública relacionada. Exclusões SHALL respeitar pedidos, histórico comercial, processamento e política de retenção vigentes.

#### Scenario: Origem pública removida

- **WHEN** a Galeria pública relacionada foi removida e a privada possui mídia própria
- **THEN** o fotógrafo continua podendo consultar e operar as pastas privadas conforme as regras de acesso e preservação

