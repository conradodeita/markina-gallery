## ADDED Requirements

### Requirement: Deploy de pagamento preserva módulos opcionais
O deploy de uma change de pagamento SHALL preservar o estado operacional pré-existente de módulos opcionais fora do escopo. O workflow MUST NOT habilitar processamento facial nem desenvolvimento RAW por padrão. Para facial, o deploy SHALL manter o valor já persistido; para RAW, SHALL detectar e manter o worker ativo, sem iniciar o worker se estiver inativo.

#### Scenario: Módulos opcionais permanecem inativos
- **WHEN** a publicação de pagamento começa com processamento facial desabilitado e worker RAW inativo
- **THEN** a publicação mantém ambos desabilitados e não inicia seus workers

#### Scenario: Módulos opcionais ativos são preservados
- **WHEN** a publicação de pagamento começa com processamento facial habilitado ou worker RAW ativo
- **THEN** a publicação mantém esses módulos no estado operacional detectado e os atualiza junto com o código

### Requirement: Escopo do release da correção InfinitePay

O release SHALL permanecer no escopo API/web existente, e o manifesto SHALL fixar os hashes exatos dos runtimes revisados. Compose pode injetar binding secreto somente na API. A change MUST NOT alterar schema/migrations, workers, Nginx ou serviços de terceiros.

#### Scenario: Gate admite somente os módulos de pagamento revisados
- **WHEN** o classificador de release avalia a correção e seus artefatos de teste/OpenSpec
- **THEN** admite somente blobs runtime com hash explícito no manifesto
- **AND** mantém a configuração do arquivo de segredo restrita ao serviço API
- **AND** não autoriza mudanças de schema, workers ou serviços de terceiros

### Requirement: Reconciliação do gate com o runtime publicado

O manifesto SHALL incluir os blobs exatos de `infinitepay_settings.py` e `payment_availability.py` da correção. A comparação SHALL distinguir a versão efetiva da API da versão web. Uma atualização web-only MUST NOT avançar a baseline da API nem ocultar dependências Python ainda não publicadas. Divergências fora do escopo SHALL manter o release bloqueado.

#### Scenario: Módulos da correção com conteúdo aprovado
- **WHEN** o delta contém os dois módulos InfinitePay com os blobs revisados e nenhum arquivo proibido
- **THEN** o gate aceita esses módulos e recusa qualquer alteração posterior de seu conteúdo sem revisão

#### Scenario: Checkout do servidor mais recente que a API
- **WHEN** o checkout/web contém uma atualização Python ausente da imagem API ativa
- **THEN** a comparação conserva a baseline efetiva da API e bloqueia o candidato que incluir essa atualização
- **AND** não declara prontidão operacional com base apenas no CI do PR

### Requirement: Operação supervisionada autorizada com dependências delimitadas

O release SHALL aceitar a janela de indisponibilidade e interrupção controlada autorizada em 21/10/2026, preservando dados, filas e imagens anteriores. API e web SHALL ter baselines verificadas separadamente. A imagem API SHALL preservar Python 3.13.16 e todas as distribuições, exceto os quatro pins Python autorizados, e passar homologação ARM64 isolada antes de substituir containers. Workers sem candidato aprovado MUST NOT ser atualizados.

#### Scenario: API candidata com distribuição adicional alterada
- **WHEN** a comparação integral de pacotes ou Python encontra mudança além de aiohttp 3.14.4, multidict 6.9.1, urllib3 2.8.0 e yarl 1.25.1
- **THEN** o release recusa a imagem antes de recriar qualquer container

#### Scenario: API e web em revisões diferentes
- **WHEN** a web avançou o checkout sem publicar dependências API
- **THEN** o gate verifica os inputs da API contra sua baseline e os inputs web contra a baseline web
- **AND** admite somente o Compose API-only e os blobs exatos revisados

#### Scenario: Manutenção com trabalho persistido
- **WHEN** há tarefas em execução na janela expressamente autorizada
- **THEN** a operação registra os estados e admite encerramento gracioso sem exigir filas vazias
- **AND** preserva callbacks/retornos pendentes para reconciliação sem reemitir compras ambíguas ou responder sucesso falso
