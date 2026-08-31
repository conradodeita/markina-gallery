## MODIFIED Requirements

### Requirement: Entrega privada por papel

O sistema SHALL entregar qualquer prévia fotográfica somente após autenticação e autorização decidida pelo backend, sem disponibilizar URL pública persistente. Uma cliente em Galeria pública `standard` SHALL receber somente fotos publicadas daquela origem; `invite_only` SHALL exigir vínculo ou convite individual compatível; `collective_protected` SHALL NOT entregar grade. Galerias privadas SHALL entregar somente suas referências disponíveis e o histórico SHALL entregar somente a prévia mínima associada ao item comercial autorizado.

#### Scenario: Prévia do cliente

- **WHEN** o cliente autorizado abre uma foto disponível em sua Galeria pública ou privada permitida
- **THEN** o sistema entrega somente a prévia protegida daquela foto e não revela outra foto, galeria ou original

#### Scenario: Prévia administrativa

- **WHEN** o fotógrafo autenticado abre uma foto para conferência administrativa
- **THEN** o sistema entrega uma prévia administrativa limitada à resolução de conferência e sem fornecer download do original

#### Scenario: Acesso indevido

- **WHEN** uma sessão sem permissão solicita uma prévia por identificador ou caminho
- **THEN** o sistema nega a solicitação sem revelar se o arquivo ou a foto existem

#### Scenario: Visitante ainda não autenticado

- **WHEN** uma pessoa abre capa ou informações de uma Galeria pública sem concluir OTP
- **THEN** o sistema não entrega capa fotográfica identificável, miniatura, grade nem visualizador e encaminha ao fluxo de autenticação quando necessário

#### Scenario: Evento coletivo protegido

- **WHEN** uma cliente autenticada solicita fotos de uma Galeria pública `collective_protected`
- **THEN** o sistema não enumera nem entrega fotos, mesmo que a cliente possua o link da origem

### Requirement: Proteção visual aplicada ao conteúdo

O sistema SHALL aplicar marca-d'água e demais proteção configurada à imagem de prévia entregue ao cliente, e não somente como camada visual do navegador. A configuração efetiva da Galeria pública SHALL ser usada por suas privadas sem override privado. A prévia histórica SHALL ser a menor representação protegida suficiente para identificação do item comprado e SHALL NOT justificar retenção de todo original.

#### Scenario: Cliente visualiza prévia protegida

- **WHEN** uma prévia é entregue ao cliente
- **THEN** a imagem recebida já contém a proteção visual configurada e não inclui EXIF/GPS

#### Scenario: Ampliação autorizada

- **WHEN** cliente ou fotógrafo amplia uma prévia permitida
- **THEN** o sistema mantém a mesma autorização e o limite de resolução correspondente ao seu papel

#### Scenario: Galeria operacional removida

- **WHEN** a cliente consulta item comprado cuja foto operacional foi apagada
- **THEN** o backend entrega somente a prévia histórica mínima protegida e a entrega ou referência final permitida pelo pedido
