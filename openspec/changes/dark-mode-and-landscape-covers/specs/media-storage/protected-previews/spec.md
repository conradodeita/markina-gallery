## MODIFIED Requirements

### Requirement: Entrega privada por papel

O sistema SHALL entregar prévias somente após autenticação e autorização da galeria derivada ou do papel administrativo, sem disponibilizar URL pública persistente. A apresentação da capa SHALL ser uma exceção de proteção visual, não de autorização ou de acesso ao original.

#### Scenario: Prévia do cliente
- **WHEN** o cliente autorizado abre uma foto atribuída à sua galeria derivada como conteúdo
- **THEN** o sistema entrega somente a prévia protegida daquela foto e não revela outra foto, galeria ou original

#### Scenario: Prévia administrativa
- **WHEN** o fotógrafo autenticado abre uma foto para conferência administrativa
- **THEN** o sistema entrega uma prévia administrativa sem marca-d'água, limitada à resolução de conferência e sem fornecer download do original

#### Scenario: Acesso indevido
- **WHEN** uma sessão sem permissão solicita uma prévia por identificador ou caminho
- **THEN** o sistema nega a solicitação sem revelar se o arquivo ou a foto existem

#### Scenario: Capa autorizada
- **WHEN** um usuário autorizado visualiza a capa vigente de sua galeria
- **THEN** recebe somente a prévia reduzida dessa capa, sem marca-d'água, grade ou EXIF/GPS, mantendo autorização e headers privados existentes

### Requirement: Proteção visual aplicada ao conteúdo

O sistema SHALL aplicar marca-d'água e demais proteção configurada à imagem de prévia de conteúdo entregue ao cliente, e não somente como camada visual do navegador. Somente a apresentação da capa vigente SHALL dispensar marca-d'água e linhas de grade. A exceção SHALL NOT desproteger fotos das pastas, miniaturas de conteúdo, ampliações, carrinho ou pedidos.

#### Scenario: Cliente visualiza prévia protegida
- **WHEN** uma prévia de conteúdo é entregue ao cliente
- **THEN** a imagem recebida já contém a proteção visual configurada e não inclui EXIF/GPS

#### Scenario: Ampliação autorizada
- **WHEN** cliente ou fotógrafo amplia uma prévia de conteúdo permitida
- **THEN** o sistema mantém a mesma autorização e o limite de resolução correspondente ao seu papel

#### Scenario: Foto legada usada como capa e conteúdo
- **WHEN** a mesma foto está selecionada como capa e também pertence ao acervo
- **THEN** somente sua apresentação como capa é limpa e sua apresentação como conteúdo continua protegida

#### Scenario: Capa já existente
- **WHEN** uma capa cadastrada possui prévia limpa pronta e o novo comportamento é publicado
- **THEN** sua apresentação passa a ser limpa sem substituir o original nem reprocessar as fotos da galeria

#### Scenario: Prévia limpa indisponível
- **WHEN** não existe prévia limpa utilizável da capa
- **THEN** o sistema indica indisponibilidade temporária, sem servir o original ou uma foto diferente
