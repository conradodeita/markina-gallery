## REMOVED Requirements

### Requirement: Propriedade exclusiva da galeria privada derivada
**Reason**: A galeria privada representa um acervo restrito compartilhável por familiares, enquanto propriedade comercial e interações pertencem individualmente a cada membro.
**Migration**: Cada privada existente recebe sua cliente atual como primeiro membro; autorização e consultas passam a usar a associação, preservando IDs, fotos e histórico.

### Requirement: Clonagem privada sem duplicação de mídia
**Reason**: Adicionar outra cliente à mesma origem não cria uma privada clonada; cria uma associação à privada compartilhada compatível com a unicidade por Galeria pública e cliente.
**Migration**: Privadas legadas permanecem distintas. Novos membros são associados à privada escolhida quando não possuírem outra privada naquela origem; nenhuma mídia é copiada.

## MODIFIED Requirements

### Requirement: Entrada por link não listado e vínculo individual
O sistema SHALL tratar links de Galeria pública e privada como localizadores opacos estáveis, revogáveis e rotacionáveis. O visitante SHALL concluir OTP antes de criar vínculo. O link público vincula somente a origem permitida; o link privado associa a cliente àquela privada e à Galeria pública de origem, desde que ela ainda não pertença a outra privada da mesma origem.

#### Scenario: Cliente entra pelo link público
- **WHEN** uma pessoa abre link público válido e conclui OTP
- **THEN** o sistema cria ou reutiliza sua identidade e vínculo com a origem sem conceder acesso a privadas existentes

#### Scenario: Cliente entra pelo link privado
- **WHEN** uma pessoa abre link privado válido, conclui OTP e não possui outra privada naquela origem
- **THEN** o sistema cria uma associação ativa à privada e à origem, sem criar cópia de fotos nem atividade comercial em seu nome

#### Scenario: Cliente entra pelo link compartilhado
- **WHEN** uma pessoa abre um link opaco válido e conclui o OTP com sucesso
- **THEN** o sistema registra somente os vínculos autorizados pelo escopo público ou privado daquele link e encaminha para o destino permitido

#### Scenario: Evento coletivo protegido
- **WHEN** o acervo representa evento coletivo protegido
- **THEN** o sistema não apresenta grade coletiva e mantém qualquer resultado facial fora do produto até aprovação do spike e change específica

### Requirement: Estados privados de descoberta e compra
O sistema SHALL apresentar o estado de cada foto exclusivamente no contexto do membro autenticado: `nova`, `visualizada mas não comprada` ou `já comprada`. Favoritos, comentários, seleção, valores, pedidos e pagamentos SHALL permanecer invisíveis aos demais membros, embora todos vejam o mesmo conjunto de fotos disponíveis da privada.

#### Scenario: Familiares revisam a mesma privada
- **WHEN** mãe e pai abrem a mesma galeria privada
- **THEN** ambos veem o acervo comum, mas cada um recebe somente seus próprios marcadores, comentários, seleção, total e histórico

#### Scenario: Cliente revisita o evento
- **WHEN** uma cliente abre novamente uma privada com fotos antigas e novas
- **THEN** a interface diferencia suas fotos compradas, ampliadas e novas sem incorporar o estado de outra cliente

## ADDED Requirements

### Requirement: Associação multiusuário com unicidade por origem
O sistema SHALL permitir vários membros em uma galeria privada e SHALL garantir, inclusive sob concorrência, no máximo uma associação privada ativa por par `Galeria pública + cliente`. A identidade SHALL ser resolvida pelo telefone E.164 verificado, não pelo nome ou token isolado.

#### Scenario: Segundo familiar ingressa
- **WHEN** um segundo telefone verificado entra pelo link da privada
- **THEN** ele se torna membro do mesmo acervo com estado individual vazio e sem modificar atividades dos membros existentes

#### Scenario: Concorrência de dois links
- **WHEN** duas requisições tentam associar o mesmo telefone a privadas distintas da mesma origem
- **THEN** o sistema converge para uma única associação e não deixa vínculo duplicado ou parcial

### Requirement: Bloqueio e desvinculação por membro
O fotógrafo SHALL poder bloquear, desbloquear ou desvincular uma cliente somente naquela privada. O bloqueio suspende navegação e novas interações sem apagar histórico; a desvinculação SHALL aplicar a política comercial, preservar cadastro e outras origens e não afetar membros restantes.

#### Scenario: Cliente bloqueada
- **WHEN** o fotógrafo bloqueia uma cliente da privada
- **THEN** ela perde o acesso operacional e não o recupera pelo mesmo ou por outro link daquela origem, enquanto pedidos e entregas históricas permanecem autorizados conforme sua política

#### Scenario: Último membro é desvinculado
- **WHEN** a última cliente é removida e não existe impedimento comercial
- **THEN** a privada permanece sob controle administrativo até exclusão explícita, sem desaparecer automaticamente

### Requirement: Acervo comum sem duplicação
O sistema SHALL manter uma única referência por justificativa autorizada para cada foto disponível na privada. Fotos adicionadas por administrador, seleção de qualquer membro ou futura origem facial aprovada integram o acervo comum sem copiar JPEG, prévia ou original; remover uma justificativa SHALL NOT eliminar referências sustentadas por outra.

#### Scenario: Fotos de pessoas diferentes
- **WHEN** uma cliente seleciona fotos de dois filhos na mesma Galeria pública
- **THEN** todas entram na mesma privada e na seleção individual da cliente, compondo um único total comercial

#### Scenario: Outro membro vê foto nova
- **WHEN** um membro adiciona uma foto à privada por seleção autorizada
- **THEN** os demais membros veem a foto como disponível, mas ela não aparece selecionada, favoritada ou comprada para eles
