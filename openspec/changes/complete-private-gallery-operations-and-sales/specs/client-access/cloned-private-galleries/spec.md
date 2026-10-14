## MODIFIED Requirements

### Requirement: Clonagem privada sem duplicação de mídia

O sistema SHALL preservar galerias privadas e referências legadas já existentes para consulta, histórico comercial e limpeza controlada, mas SHALL NOT permitir ao fotógrafo criar uma nova galeria privada clonando fotos de uma Galeria pública ou de outra privada. Uma nova privada administrativa SHALL nascer vazia para receber novos JPEGs do dispositivo; a seleção consciente da cliente na Galeria pública SHALL continuar criando ou atualizando automaticamente sua privada correspondente.

#### Scenario: Fotógrafo tenta clonar acervo existente

- **WHEN** o fotógrafo chama a operação legada de clonagem de uma galeria privada para outra cliente
- **THEN** o backend recusa a criação sem copiar arquivo, referência, seleção, compra ou histórico

#### Scenario: Segunda responsável recebe privada vazia

- **WHEN** o fotógrafo cria uma privada para uma segunda responsável sem fotos selecionadas por ela
- **THEN** a privada pode permanecer vazia e receber somente novos uploads próprios do dispositivo

#### Scenario: Segunda responsável recebe acesso

- **WHEN** o fotógrafo autoriza uma segunda responsável no mesmo evento
- **THEN** ela recebe vínculo e estado próprios, sem herdar por clonagem as fotos, seleções ou compras de outra responsável

#### Scenario: Cliente seleciona foto da Galeria pública

- **WHEN** uma cliente autorizada seleciona uma foto disponível na Galeria pública
- **THEN** o sistema cria ou reutiliza sua privada, referencia a foto pela origem `client` e mantém seleção, pedido e histórico individuais

#### Scenario: Foto vendida a mais de uma pessoa

- **WHEN** responsáveis diferentes selecionam e compram conscientemente a mesma foto autorizada na Galeria pública
- **THEN** cada privada e cada pedido preservam seu próprio registro comercial sem revelar compradores entre clientes
