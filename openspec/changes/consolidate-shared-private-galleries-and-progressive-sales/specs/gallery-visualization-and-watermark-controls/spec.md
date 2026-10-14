## MODIFIED Requirements

### Requirement: Configuração visual e marca-d’água
O sistema SHALL permitir configurar proteção global e, por Galeria pública, capa, título e tipografia escolhida de lista segura ampliada com famílias neutras, editoriais e manuscritas locais. A privada SHALL herdar apresentação e proteção vigentes; quando a origem for removida, SHALL usar o último snapshot efetivo necessário à continuidade. Nenhum campo SHALL aceitar fonte remota, CSS livre ou família arbitrária.

#### Scenario: Carregamento direto
- **WHEN** o fotógrafo clica em `Carregar fotos`
- **THEN** o seletor local abre e os JPEGs são registrados na pasta atual

#### Scenario: Lista ampliada
- **WHEN** o fotógrafo abre a tipografia do título
- **THEN** a lista apresenta no mínimo oito opções controladas, incluindo ao menos três manuscritas, com rótulo de categoria e fallback local

#### Scenario: Origem removida
- **WHEN** uma Galeria pública é removida e sua privada permanece ativa
- **THEN** a privada conserva capa, organização, título e tipografia do último estado efetivo sem depender da entidade operacional removida

### Requirement: Visualização da galeria
O sistema SHALL permitir abrir link opaco e exigir autenticação antes de prévias. Fotógrafo e clientes autorizadas SHALL receber composição responsiva com capa, pastas, grade sem moldura dominante, espaçamento consistente e imagens preservadas; membros da mesma privada recebem o acervo comum com marcadores individuais.

#### Scenario: Modo individual
- **WHEN** a galeria usa pastas individuais
- **THEN** capa e pastas autorizadas aparecem com nome, contagem e fotos adaptadas às proporções

#### Scenario: Modo sequencial
- **WHEN** a galeria usa sequência
- **THEN** cada pasta aparece em ordem com título e grade contínua

#### Scenario: Smartphone
- **WHEN** a galeria é aberta em viewport móvel
- **THEN** grade, rodapé, marcadores e visualizador permanecem tocáveis e sem rolagem horizontal

#### Scenario: Estado por membro
- **WHEN** dois membros abrem a mesma foto
- **THEN** cada sessão recebe somente seus indicadores de favorito, seleção e compra
