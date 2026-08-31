# gallery-sales/original-gallery-experience Specification

## Purpose
Definir a experiência visual autoral e utilizável que conecta a operação do fotógrafo e a jornada privada da cliente aos dados autorizados do produto.

## Requirements

### Requirement: Interface original por papel
O sistema SHALL fornecer uma interface visual coesa para fotógrafo e cliente, com navegação, hierarquia, componentes e estados próprios da Markina Gallery. A interface SHALL ser responsiva, acessível e não copiar componentes ou código de serviços concorrentes.

#### Scenario: Fotógrafo inicia a operação
- **WHEN** o fotógrafo autenticado abre a área administrativa
- **THEN** ele vê acesso claro a pendências, galerias, clientes, pastas e operações disponíveis para seus dados autorizados

#### Scenario: Cliente retoma sua jornada
- **WHEN** uma cliente autenticada abre sua biblioteca ou galeria privada
- **THEN** ela vê apenas sua jornada de revisão, seleção e histórico, sem controles administrativos ou dados de terceiros

### Requirement: Estados visuais controlados pelo backend
O sistema SHALL apresentar carregamento, vazio, erro, sucesso, bloqueio, expiração e preparação a partir de respostas autorizadas do backend. O frontend SHALL NOT preencher lacunas com autorizações, fotos, pedidos ou estados simulados persistentes.

#### Scenario: Falha de consulta operacional
- **WHEN** uma consulta autenticada de galeria ou pasta falha
- **THEN** a interface informa a falha e oferece uma ação segura de nova tentativa sem exibir dados obsoletos como se fossem atuais

### Requirement: Validação na interface entregue
O sistema SHALL disponibilizar dados sintéticos e um roteiro de validação manual para que fotógrafo e cliente avaliem o fluxo na interface entregue, antes de essa interface ser considerada aceita.

#### Scenario: Homologação visual
- **WHEN** a versão visual é publicada em homologação
- **THEN** o roteiro identifica os dois papéis, os estados esperados e os limites de dados sintéticos para a revisão humana
