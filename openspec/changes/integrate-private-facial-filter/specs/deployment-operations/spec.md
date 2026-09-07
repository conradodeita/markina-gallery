## ADDED Requirements

### Requirement: Runtime facial opcional e fechado por padrão

O ambiente SHALL exigir configuração explícita para habilitar processamento facial. Ausência ou divergência de chave criptográfica, modelo, hash, política ou ambiente MUST falhar fechada, mantendo API, mídia e seleção manual saudáveis. Nenhum segredo, peso ou embedding SHALL ser incluído no frontend ou no Git.

#### Scenario: Configuração incompleta

- **WHEN** o worker inicia sem todos os parâmetros faciais válidos
- **THEN** o subsistema facial fica indisponível com diagnóstico sanitizado e os demais healthchecks permanecem independentes

### Requirement: Fila facial isolada sem nova exposição de rede

O processamento SHALL usar fila bloqueante de baixa prioridade, concorrência e recursos limitáveis, sem publicar porta adicional. O worker SHALL permanecer sem consumo ativo de CPU quando a fila estiver vazia, descarregar modelos após ocioso configurável e SHALL NOT varrer continuamente galerias sem mudanças. Healthcheck e métricas SHALL distinguir fila, índice, limpeza e modelo sem expor dado biométrico ou interferir em containers, redes e volumes de terceiros.

#### Scenario: Pico de uploads

- **WHEN** prévias e indexações concorrem por recursos
- **THEN** a geração de prévias e as rotas interativas têm prioridade, e a fila facial desacelera sem tornar a galeria indisponível

#### Scenario: Gate alterado com processos persistentes

- **WHEN** uma operação autorizada habilita, pausa, restaura ou encerra o processamento facial
- **THEN** API, worker de mídia e worker facial aplicável recebem o mesmo gate vigente, e a operação verifica a configuração efetiva sem publicar porta ou reiniciar serviço de terceiro

#### Scenario: Fila vazia

- **WHEN** não existem jobs faciais pendentes durante o prazo ocioso configurado
- **THEN** o worker descarrega os modelos, não inicia scan de galeria e mantém somente o consumo mínimo necessário para aguardar trabalho

### Requirement: Operação reversível e verificável

Deploy SHALL exigir inventário, backup, migration aditiva, modelos verificados por hash, feature flag desligada e smoke inicial sem dados pessoais. Uma carga real de adultos ou menores em homologação SHALL começar somente após autorização humana explícita da execução e registro de responsável, origem, finalidade, quantidade, identificador interno e retenção do lote, sob acesso autenticado, criptografia e exclusão controlada. Rollback SHALL desligar novas operações e preservar estruturas para limpeza controlada, sem down migration destrutiva nem perda de histórico comercial.

#### Scenario: Carga real controlada em homologação

- **WHEN** o administrador/fotógrafo apresenta um lote real documentado e a execução é autorizada no ambiente privado de homologação
- **THEN** o sistema limita o tratamento ao lote e à janela aprovados, coleta somente métricas agregadas e exige prova de limpeza e desativação dos gates temporários ao final

#### Scenario: Transição do piloto legado antes do deploy privado

- **WHEN** homologação ainda executa o piloto facial legado fora do gate privado e um SHA autorizado precisa publicar a operação vinculada a lote
- **THEN** uma transição explícita e auditável desliga somente `FACIAL_PROCESSING_ENABLED`, interrompe somente o `face-worker`, recria somente a API da Markina e mantém as fotos intactas, sem reativação automática depois do deploy

#### Scenario: Piloto privado ativo durante deploy comum

- **WHEN** `FACIAL_HOMOLOG_PRIVATE_MODE=true` ou a transição legada não foi explicitamente autorizada
- **THEN** o deploy comum continua falhando antes de trocar código ou banco e exige o fechamento ou procedimento de upgrade privado aplicável

#### Scenario: Rollback da funcionalidade

- **WHEN** o operador aciona o rollback facial
- **THEN** consultas e indexações param, temporários são limpos, o produto retorna à seleção manual e nenhum serviço externo à Markina é alterado

#### Scenario: Fotos prontas sem evento facial durante lote ativo

- **WHEN** o inventário detecta que um lote privado ainda autorizado concluiu prévias enquanto o worker de mídia mantinha o gate antigo
- **THEN** uma reconciliação explícita, vinculada ao mesmo SHA, lote, autorização, quantidade e declaração de menores, enfileira idempotentemente somente as fotos daquela janela sem apagar mídia, repetir upload, ampliar prazo ou interromper a geração de prévias
