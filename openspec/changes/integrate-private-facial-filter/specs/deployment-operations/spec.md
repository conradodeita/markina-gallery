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

#### Scenario: Fila vazia

- **WHEN** não existem jobs faciais pendentes durante o prazo ocioso configurado
- **THEN** o worker descarrega os modelos, não inicia scan de galeria e mantém somente o consumo mínimo necessário para aguardar trabalho

### Requirement: Operação reversível e verificável

Deploy SHALL exigir inventário, backup, migration aditiva, modelos verificados por hash, feature flag desligada e smoke sintético sem crianças. Rollback SHALL desligar novas operações e preservar estruturas para limpeza controlada, sem down migration destrutiva nem perda de histórico comercial.

#### Scenario: Rollback da funcionalidade

- **WHEN** o operador aciona o rollback facial
- **THEN** consultas e indexações param, temporários são limpos, o produto retorna à seleção manual e nenhum serviço externo à Markina é alterado
