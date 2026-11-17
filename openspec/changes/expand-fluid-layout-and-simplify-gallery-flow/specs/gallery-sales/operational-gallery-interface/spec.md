## ADDED Requirements

### Requirement: Capa dedicada por upload

Na etapa 03, o fotógrafo SHALL definir ou substituir a capa enviando um JPEG do dispositivo à pasta técnica. Detalhes SHALL NOT listar fotos de conteúdo como candidatas. O upload aceito SHALL tornar-se a capa vigente e exibir processamento e prévia protegida, sem segunda escolha. Tipografia e posição do título permanecem independentes.

#### Scenario: Galeria com muitas fotos de conteúdo

- **WHEN** o fotógrafo abre a etapa 03 de uma galeria com milhares de fotos nas pastas
- **THEN** a etapa carrega somente configuração e estado da capa vigente, sem consultar ou renderizar o acervo como candidatas

#### Scenario: Fotógrafo envia nova capa

- **WHEN** um JPEG válido é enviado pelo dispositivo
- **THEN** o sistema registra a intenção, processa o derivado protegido e apresenta a nova capa quando pronta, sem seleção adicional

#### Scenario: Capa ainda em processamento

- **WHEN** a nova capa foi aceita e o derivado ainda não está pronto
- **THEN** a etapa mostra o processamento, mantém controles tipográficos utilizáveis e atualiza a prévia após confirmação do backend

### Requirement: Capa legada permanece compatível

Uma capa preexistente de conteúdo SHALL continuar legível até ser substituída, mas MUST NOT voltar a aparecer como opção de origem na etapa 03.

#### Scenario: Galeria com capa legada

- **WHEN** a galeria já aponta para uma foto de conteúdo como capa antes desta mudança
- **THEN** a apresentação continua usando essa capa até novo upload e a etapa 03 não lista outras fotos de conteúdo

### Requirement: Imagens sem ação duplicada de capa

Na etapa 04, o sistema SHALL apresentar operações de pasta e foto, mas SHALL NOT oferecer `Usar como capa`, `Capa atual` ou ação equivalente. A gestão de capa existe somente na etapa 03.

#### Scenario: Fotógrafo abre uma pasta na etapa 04

- **WHEN** as prévias das fotos correspondentes são exibidas
- **THEN** cada foto mantém suas ações de mídia permitidas e nenhuma oferece definição ou indicação operacional de capa

### Requirement: Comentário no cartão do pedido

Em Vendas e pagamentos, o cartão de foto comprada SHALL mostrar o comentário ativo mais recente da cliente para aquela foto e escopo do pedido, limitado a 50 caracteres incluindo reticências, abaixo do nome e do valor unitário. O comentário MUST NOT cobrir a miniatura ou a imagem ampliada. A experiência da cliente SHALL permanecer inalterada.

#### Scenario: Cliente comentou uma foto comprada

- **WHEN** o fotógrafo abre os detalhes de um pedido com foto comentada
- **THEN** o trecho de até 50 caracteres aparece abaixo do nome e do preço, fora da miniatura e da imagem ampliada, sem exibir comentário de outra cliente

#### Scenario: Cliente deixou mais de um comentário na mesma foto

- **WHEN** a mesma cliente possui vários comentários ativos para a foto e o escopo do pedido
- **THEN** o cartão mostra somente o comentário mais recente abaixo do valor, truncado sem exceder 50 caracteres, enquanto o texto integral permanece no fluxo de comentários já existente

### Requirement: Favorito na prévia do pedido

Em Vendas e pagamentos, a prévia SHALL mostrar um coração quando a cliente favoritou a foto. O favorito MUST respeitar o mesmo escopo de tenant, cliente, foto e pedido.

#### Scenario: Cliente favoritou uma foto comprada

- **WHEN** o fotógrafo abre um pedido cuja cliente favoritou uma foto
- **THEN** a prévia correspondente mostra o coração e não mistura favoritos de outras clientes ou galerias

### Requirement: Sobreposição segura em HTML independente

O HTML de fotos compradas SHALL repetir comentário e favorito sobre cada prévia, escapar o comentário, preservar `private, no-store` e aplicar a cor de destaque selecionada. Sem prévia disponível, nenhum overlay SHALL ser renderizado.

#### Scenario: HTML de fotos compradas

- **WHEN** o fotógrafo baixa o HTML de fotos compradas
- **THEN** cada prévia correspondente mostra as mesmas interações específicas daquela cliente e pedido, com comentário escapado como texto e cor de destaque da aparência escolhida no painel

#### Scenario: Sem interação ou sem prévia disponível

- **WHEN** não há comentário nem favorito da cliente para a foto, ou a mídia da prévia está indisponível
- **THEN** a interface não inventa interação nem sobrepõe texto em um espaço sem foto, e mantém o estado de mídia já apresentado

### Requirement: Acervo privado organiza as ações da pasta

Em `Clientes vinculadas` → `Acervo da cliente`, o painel expandido de cada pasta privada SHALL agrupar o estado da pasta, as ações de gestão, o prazo e o acervo de fotos com hierarquia visual consistente. Ações principais SHALL usar os estilos comuns de botão e manter rótulos e semântica acessíveis. Em viewports estreitas, os controles SHALL quebrar ou empilhar sem overflow horizontal.

#### Scenario: Fotógrafo abre as ações de uma pasta privada

- **WHEN** o fotógrafo expande uma pasta no `Acervo da cliente`
- **THEN** `Processamento da pasta` e `Disponibilizar fotos prontas` aparecem no mesmo grupo, com altura, espaçamento e estilo de botão coerentes com o painel

#### Scenario: Card de pasta em tela estreita

- **WHEN** o fotógrafo abre o card em smartphone ou viewport estreita
- **THEN** as ações, a configuração de prazo e a grade de fotos se reorganizam sem texto ou botões cortados e sem overflow horizontal

### Requirement: Campo numérico de prazo usa espaço proporcional

O campo de dias de acesso SHALL ocupar somente a largura útil para um valor numérico curto e exibir a unidade `dias` junto ao controle, sem reduzir sua acessibilidade ou precisão.

#### Scenario: Fotógrafo define dias de acesso

- **WHEN** o fotógrafo informa a validade de uma pasta
- **THEN** vê um controle compacto, legível e associado ao rótulo de dias, com a orientação da regra posicionada separadamente

### Requirement: Configurações agrupam opções por finalidade e prioridade

A página Configurações SHALL organizar opções em grupos recolhíveis com títulos e descrições curtas. Primeiros passos SHALL começar aberto e os demais grupos fechados. O resumo obrigatório SHALL permanecer no início e o aceite completo/histórico de Termos na última seção. A organização MUST NOT alterar acesso, pagamentos ou onboarding.

#### Scenario: Estado inicial compacto
- **WHEN** fotógrafo abre Configurações sem fragmento de destino
- **THEN** encontra Primeiros passos expandido e os títulos dos demais grupos recolhidos, com Termos no fim

### Requirement: Grupos recolhíveis preservam navegação e formulários

Cada grupo SHALL abrir/recolher por teclado ou toque, independentemente dos demais, sem desmontar formulários ou perder dados preenchidos. Atalhos e fragmentos de URL SHALL abrir os ancestrais recolhidos do destino e posicioná-lo na tela, incluindo PIX, WhatsApp, onboarding e Termos.

#### Scenario: Fotógrafo recolhe um grupo
- **WHEN** fotógrafo preenche um campo e recolhe e reabre o grupo
- **THEN** o valor preenchido permanece disponível e os outros grupos mantêm seu estado

#### Scenario: Atalho para grupo recolhido
- **WHEN** fotógrafo usa um atalho ou abre URL com fragmento para uma configuração
- **THEN** o grupo correspondente é aberto e o destino fica visível sem perda do estado dos demais grupos

#### Scenario: Fotógrafo localiza uma configuração

- **WHEN** o fotógrafo abre Configurações em desktop ou smartphone
- **THEN** encontra primeiro os passos para preparar a conta e pode navegar por grupos de segurança/acesso, comunicação, recebimentos, marca/aparência e encerramento

#### Scenario: Fotógrafo consulta ou aceita os Termos

- **WHEN** o fotógrafo escolhe a etapa Termos no resumo ou percorre a página até o fim
- **THEN** é levado à seção final, onde consulta o estado, histórico, cópia e aceite vigente sem duplicação do conteúdo jurídico em outra seção
