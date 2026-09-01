## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface orientada pela Galeria pública para criar e operar clientes, galerias privadas, pastas e JPEGs. O editor SHALL manter as etapas Ajustes, Vendas, Detalhes e apresentação, Imagens e pastas, e Clientes e acesso; cada etapa SHALL apresentar somente dados persistidos e capacidades autorizadas pelo backend. A interface SHALL permitir retornar, avançar e concluir sem duplicar galeria, pasta, foto, vínculo, seleção ou pedido.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui uma ação válida em qualquer etapa
- **THEN** o sistema persiste somente a entidade afetada, confirma o resultado e mantém a mesma Galeria pública como contexto

#### Scenario: Segunda responsável

- **WHEN** o fotógrafo cria uma galeria privada para uma nova cliente a partir de fotos da mesma Galeria pública
- **THEN** o sistema cria ou reutiliza uma privada independente sem alterar seleção, prazo, pedido ou histórico de outra cliente

#### Scenario: Pasta em preparação

- **WHEN** o fotógrafo abre uma pasta com fotos ainda não publicadas
- **THEN** ele vê JPEGs, processamento e ações administrativas sem expor esse conteúdo à cliente

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos nem fotos fora das Galerias públicas e privadas autorizadas para sua identidade

#### Scenario: Continuidade entre etapas

- **WHEN** o fotógrafo retorna a uma etapa já preenchida ou conclui o editor
- **THEN** a interface recupera os valores persistidos e não usa estado local como fonte de verdade

## ADDED Requirements

### Requirement: Configuração comercial completa na etapa Vendas

O sistema SHALL apresentar e persistir na etapa Vendas as faixas contíguas de preço em centavos, instruções PIX manual, texto comercial, prazo padrão de seleção e controles suportados de favoritos e comentários. O backend SHALL calcular totais, validar faixas e alertar saltos comerciais; salvar a configuração SHALL NOT criar, confirmar nem alterar pedido existente.

#### Scenario: Fotógrafo abre Vendas

- **WHEN** o backend declara a capacidade comercial disponível
- **THEN** a etapa exibe os valores atuais, permite editá-los e não apresenta o estado falso de funcionalidade indisponível

#### Scenario: Faixa possui salto comercial

- **WHEN** aumentar a quantidade mínima de uma faixa reduz o total calculado
- **THEN** a interface alerta o fotógrafo antes do salvamento e o backend mantém a validação da decisão

#### Scenario: Configuração comercial é salva

- **WHEN** o fotógrafo envia faixas, PIX, mensagem, prazo e interações válidos
- **THEN** a etapa confirma a persistência e pedidos anteriores mantêm seus snapshots imutáveis

### Requirement: Capa configurável antes da etapa Imagens

O sistema SHALL permitir na etapa Detalhes e apresentação enviar uma imagem de capa dedicada ou escolher uma foto processada já pertencente à Galeria pública. A mesma etapa SHALL apresentar prévia imediata com o título, a posição, a cor, o tamanho e a tipografia selecionados. Uma imagem enviada somente como capa SHALL permanecer fora das coleções de fotos até ser explicitamente adicionada como conteúdo.

#### Scenario: Primeira configuração sem fotos

- **WHEN** a Galeria pública ainda não possui pasta de conteúdo e o fotógrafo envia um JPEG válido como capa
- **THEN** o sistema processa uma prévia protegida, permite selecioná-la e atualiza a composição da etapa 03 sem exigir navegação pela etapa 04

#### Scenario: Escolha entre fotos existentes

- **WHEN** a Galeria pública já possui fotos processadas
- **THEN** a etapa apresenta as opções autorizadas e permite trocar a capa sem mover ou duplicar o arquivo escolhido

#### Scenario: Prévia do título

- **WHEN** o fotógrafo altera tipografia, posição, cor ou tamanho
- **THEN** a prévia atualiza visualmente antes do salvamento e o backend valida somente valores controlados

### Requirement: Imagens e organização no mesmo contexto

O sistema SHALL concentrar na etapa Imagens e pastas a criação e ordenação de pastas, a escolha de organização suportada, o upload, o processamento, a revisão, a publicação e a exclusão elegível. A etapa SHALL NOT solicitar que o fotógrafo escolha galerias privadas como destino da publicação.

#### Scenario: Organização das pastas

- **WHEN** o fotógrafo escolhe pastas lado a lado ou sequência cronológica na etapa Imagens
- **THEN** o sistema persiste a escolha da Galeria pública e a prévia administrativa representa a nova organização

#### Scenario: Publicação sem destino privado

- **WHEN** o fotógrafo publica uma pasta ou uma rodada pronta
- **THEN** as fotos elegíveis passam a integrar o conteúdo publicado da Galeria pública conforme o modo de acesso, sem criar referências privadas em massa

### Requirement: Ações funcionais por cliente

O sistema SHALL permitir ao fotógrafo desvincular uma cliente e criar ou atualizar sua galeria privada com fotos publicadas, usando respostas, inventário, progresso e bloqueios decididos pelo backend. As ações SHALL atualizar o cartão ao concluir e SHALL preservar cadastro, outras galerias e histórico comercial conforme as regras de ciclo de vida vigentes.

#### Scenario: Cliente é desvinculada

- **WHEN** o fotógrafo confirma uma desvinculação elegível
- **THEN** a interface acompanha a operação até o estado terminal e remove o vínculo visual somente depois da confirmação do backend

#### Scenario: Desvinculação bloqueada por pagamento

- **WHEN** existe comunicação financeira em revisão que impede a remoção
- **THEN** o sistema preserva o cartão, explica o bloqueio e oferece somente as ações devolvidas pelo backend

#### Scenario: Fotógrafo disponibiliza fotos

- **WHEN** o fotógrafo escolhe uma cliente e uma ou mais fotos publicadas da mesma Galeria pública
- **THEN** o sistema cria ou reutiliza a galeria privada, adiciona as referências administrativas sem seleção automática e atualiza os contadores

### Requirement: Resumo administrativo acionável da Galeria pública

O sistema SHALL apresentar no resumo da Galeria pública pastas clicáveis com miniatura de capa, nome, contagens e estado; ao abrir uma pasta, o fotógrafo SHALL poder visualizar suas fotos, carregar novas fotos e excluir itens elegíveis. O resumo SHALL reutilizar cartões de clientes com disponíveis, selecionadas, compradas, estado da galeria e situação comercial consolidada, sem consultas por cliente em cascata.

#### Scenario: Pasta aparece no resumo

- **WHEN** uma pasta possui foto processada
- **THEN** o card mostra miniatura protegida e abre a gestão da mesma pasta dentro da Galeria pública

#### Scenario: Pasta publicada recebe fotos adicionais

- **WHEN** o fotógrafo abre uma pasta publicada pelo resumo e carrega novos JPEGs
- **THEN** as fotos anteriores permanecem visíveis, os novos arquivos ficam em preparação e podem ser revisados antes de uma nova publicação

#### Scenario: Cliente com atividade comercial

- **WHEN** uma cliente possui seleção, compra ou pagamento associado à Galeria pública
- **THEN** seu card mostra contagens e estado textual de pagamento ou prazo, e o nome abre a galeria privada quando ela existir
