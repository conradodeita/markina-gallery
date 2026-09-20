## ADDED Requirements

### Requirement: Fonte temporária com retenção e pressão de admissão

Fotos aderentes ao pipeline high-res SHALL possuir lifecycle durável com fonte validada, análise, derivados, ajuste vigente e descarte. O sistema SHALL preservar a fonte para retry enquanto necessária, remover após verificar artefatos duráveis, impor TTL a órfãos/falhas e proteger admissão por quotas e reserva de disco. SHALL NOT manter cópia high-res escondida. Fontes legadas SHALL NOT ser eliminadas retroativamente.

#### Scenario: Processamento completo
- **WHEN** análise, derivados e ajuste habilitado terminam com arquivos duráveis válidos
- **THEN** somente a fonte temporária correspondente é removida de modo idempotente

#### Scenario: Falha ou leitura ativa
- **WHEN** uma etapa ainda usa a fonte ou exige retry
- **THEN** a remoção normal aguarda, e expiração controlada registra necessidade de reupload sem falso sucesso

#### Scenario: Pressão de armazenamento
- **WHEN** quota de fontes, fila ou reserva de disco impede processamento seguro
- **THEN** o upload é recusado como retentável antes da persistência integral e lotes progridem conforme capacidade liberada

### Requirement: Geometria durável e apresentação independente

Derivados novos SHALL preservar aspect ratio da geometria orientada, com maior lado de aproximadamente 1980 e compressão adaptativa sem piso de bytes rígido. Ajustes fotométricos SHALL NOT invalidar índice. Transformações geométricas posteriores MUST mapear regiões ou ser recusadas.

#### Scenario: Proteção alterada após descarte
- **WHEN** a marca ou exposição muda e a fonte high-res já foi removida
- **THEN** a apresentação usa o derivado limpo durável e não provoca detecção facial

#### Scenario: Motor muda dimensões
- **WHEN** o motor retorna geometria diferente sem transformação correspondente
- **THEN** o resultado é recusado e a apresentação convencional permanece disponível

#### Scenario: Upload interrompido e reiniciado
- **WHEN** o administrador retoma os mesmos bytes JPEG na mesma pasta
- **THEN** a chave de conteúdo reutiliza o ativo, a quota é reavaliada em reupload após descarte e fragmentos próprios abandonados expiram pelo TTL

#### Scenario: Worker de mídia interrompido
- **WHEN** um job aderente fica em processamento por mais de dez minutos sem lock de execução ativo ou falha de forma transitória
- **THEN** ele pode retomar até três tentativas por geração, preservando os artefatos já confirmados e sem interferir em jobs legados
