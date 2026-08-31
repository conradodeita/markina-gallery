## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface original para criar e operar clientes, Galerias públicas compartilháveis, galerias privadas, pastas e JPEGs. A interface SHALL apresentar fluxo claro de criação, edição, preparação, liberação, criação privada administrativa, desvinculação e exclusão, sem expor acervos a clientes antes da autorização e liberação aplicáveis. Todo texto visível SHALL usar “Cliente” no lugar de “Responsável” e “Galeria pública” no lugar de “Galeria-mãe” ou “Acervo-fonte”.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui o fluxo administrativo com dados válidos
- **THEN** o sistema cria somente as referências privadas escolhidas e apresenta confirmação ou erro acessível

#### Scenario: Segunda responsável

- **WHEN** o fotógrafo cria uma galeria privada para um novo cliente a partir de fotos da mesma Galeria pública
- **THEN** o sistema exige ao menos uma foto, cria ou reutiliza a galeria privada independente do novo cliente e não altera seleção, prazo, pedido ou histórico do primeiro

#### Scenario: Pasta em preparação

- **WHEN** o fotógrafo abre uma pasta ainda não liberada
- **THEN** ele vê os JPEGs, o estado de processamento e as ações de edição ou liberação disponíveis somente para ele

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos nem fotos fora das Galerias públicas e privadas autorizadas para sua identidade e das pastas publicadas conforme o modo de acesso

#### Scenario: Terminologia padronizada

- **WHEN** fotógrafo ou cliente visualiza uma tela, mensagem, validação ou ação relacionada à pessoa vinculada
- **THEN** a interface usa “Cliente” e “Galeria pública” e não apresenta “Responsável”, “Galeria-mãe” ou “Acervo-fonte” como denominações de produto

#### Scenario: Criação administrativa da galeria privada

- **WHEN** o fotógrafo seleciona uma cliente e fotos autorizadas dentro da Galeria pública
- **THEN** a interface cria a galeria privada exclusiva, mostra confirmação e permite abrir sua ficha sem conceder acesso a outras clientes

### Requirement: Configuração administrativa do modo de acesso e modelo herdado

O sistema SHALL permitir ao fotógrafo configurar no backend cada Galeria pública como `standard`, `invite_only` ou `collective_protected` e SHALL apresentar claramente o efeito do modo antes de publicar. A mesma ficha SHALL concentrar o modelo herdado por suas privadas: preço/faixas, PIX, mensagens, favoritos, comentários, apresentação visual e prazo padrão. A interface SHALL NOT inferir permissões nem manter configuração simulada no browser.

#### Scenario: Fotógrafo escolhe modo padrão

- **WHEN** o fotógrafo salva `standard` e publica fotos para navegação manual
- **THEN** a interface informa que qualquer cliente autenticada por link válido poderá ser vinculada e navegar somente pelo conteúdo publicado

#### Scenario: Fotógrafo escolhe somente convite

- **WHEN** o fotógrafo salva `invite_only`
- **THEN** a interface informa que apenas clientes previamente associadas ou com convite individual compatível poderão navegar pelas fotos

#### Scenario: Fotógrafo escolhe evento coletivo protegido

- **WHEN** o fotógrafo salva `collective_protected`
- **THEN** a interface informa que nenhuma grade será entregue a clientes e que resultado privado depende de fluxo facial futuro aprovado

#### Scenario: Configuração privada sem duplicação

- **WHEN** o fotógrafo abre uma galeria privada derivada
- **THEN** a interface apresenta a configuração herdada da Galeria pública e direciona alterações ao modelo da origem, sem formulário de override privado nesta change

### Requirement: Interface orientada pelo backend

O sistema SHALL obter dados, permissões, disponibilidade e resultados de ações administrativas exclusivamente de APIs autenticadas do backend. A interface SHALL NOT criar autorização, registros, métricas, progresso de upload ou liberação simulados no browser.

#### Scenario: Estado administrativo

- **WHEN** o fotógrafo abre ou altera uma tela operacional
- **THEN** a interface consulta o backend e apresenta o estado retornado, sem criar autorização ou registros simulados no browser

#### Scenario: Consulta por responsável

- **WHEN** o fotógrafo busca por nome ou telefone na ficha de uma Galeria pública
- **THEN** o sistema retorna somente vínculos, contadores e estados autorizados da consulta e permite abrir a ficha individual da seleção

### Requirement: Exclusão segura de galeria privada

O sistema SHALL permitir ao fotógrafo excluir uma Galeria pública em uma única operação confirmada, mesmo quando ela possuir clientes, galerias privadas, pastas, fotos, seleções ou pedidos. A operação SHALL encerrar e ocultar a origem pública, revogar seus links e vínculos públicos, remover em cascata somente fotos e pastas sem referência privada, e preservar sem duplicação as galerias privadas e os ativos que elas ainda utilizam. Clientes e histórico comercial SHALL permanecer. O sistema SHALL impedir novas operações na origem durante a exclusão e SHALL permitir repetição segura após falha parcial.

#### Scenario: Galeria com conteúdo operacional

- **WHEN** o fotógrafo confirma a exclusão de uma galeria com pastas, fotos e clientes vinculados
- **THEN** o sistema bloqueia novas alterações públicas, desvincula os clientes da origem, remove o conteúdo sem referência privada e mantém cada galeria privada com suas fotos disponíveis para a proprietária, sem exigir ações manuais prévias

#### Scenario: Foto derivada permanece sem duplicação

- **WHEN** uma foto da Galeria pública excluída ainda está disponível em uma ou mais galerias privadas
- **THEN** o sistema mantém um único ativo físico referenciado por essas privadas, conserva sua visualização autorizada e não cria uma cópia por galeria ou cliente

#### Scenario: Histórico de compra preservado

- **WHEN** o fotógrafo exclui uma galeria com pedido confirmado
- **THEN** o sistema preserva pedido, pagamento, itens, valores, cliente, entrega e evidência visual histórica, além da mídia ainda necessária a privada ativa, removendo somente a origem pública e a mídia sem referência

#### Scenario: Falha parcial de exclusão

- **WHEN** a remoção física ou lógica falha depois de a exclusão ser iniciada
- **THEN** o sistema mantém a galeria indisponível, registra o ponto de falha e permite retomar a mesma operação sem duplicar histórico nem apagar dados de terceiros

#### Scenario: Confirmação informativa

- **WHEN** o fotógrafo inicia a exclusão da Galeria pública
- **THEN** a interface apresenta em uma única confirmação os totais de pastas, fotos, clientes, seleções e compras, distingue o que será removido do que será preservado e informa que a ação operacional é irreversível

## ADDED Requirements

### Requirement: Resumo operacional por cliente

O sistema SHALL apresentar cada cliente vinculado em componente responsivo e visualmente separado, contendo nome acionável, telefone quando autorizado, total de fotos selecionadas, total de fotos compradas, estado da galeria privada e ação de desvinculação. Os contadores e estados SHALL ser calculados pelo backend a partir da regra de negócio vigente.

#### Scenario: Cliente com galeria ativa

- **WHEN** a galeria privada permite acesso e o prazo de seleção não expirou
- **THEN** o cartão apresenta “Galeria ativa” em verde, “Selecionadas” e “Compradas” com seus totais e abre a galeria privada ao acionar o nome

#### Scenario: Cliente com galeria expirada

- **WHEN** o prazo de seleção da galeria privada terminou sem bloqueio administrativo
- **THEN** o cartão apresenta “Galeria expirada” em amarelo e preserva os contadores consolidados

#### Scenario: Cliente com galeria bloqueada

- **WHEN** o acesso da galeria privada está desabilitado pelo fotógrafo ou por regra operacional
- **THEN** o cartão apresenta “Galeria bloqueada” em preto com contraste acessível

#### Scenario: Vínculo ainda sem galeria privada

- **WHEN** a cliente concluiu o vínculo e ainda não selecionou fotos, exista ou não galeria privada administrativa com fotos disponíveis
- **THEN** o cartão apresenta “Sem seleção” em estado neutro, mostra seleção zerada, preserva a galeria administrativa quando existir e mantém somente as ações aplicáveis

#### Scenario: Cadastro ainda pendente

- **WHEN** o cadastro ou convite da cliente ainda não foi validado
- **THEN** o cartão apresenta “Cadastro pendente” em estado neutro e não inventa galeria privada nem contadores
