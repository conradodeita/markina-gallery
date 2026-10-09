## ADDED Requirements

### Requirement: Compatibilidade com inventário e limpeza de homologação
O inventário SHALL classificar explicitamente as oito tabelas técnicas do monitor como preservadas. Limpeza de dados operacionais MUST preservar propriedade, concessões, métricas, incidentes e auditoria administrativa do monitor. Sinais de sessões de clientes removidas SHALL acompanhar a exclusão dessas sessões por FK; sinais administrativos válidos SHALL permanecer.

#### Scenario: Inventário e limpeza sintética após a migration
- **WHEN** o schema inclui a migration do monitor e uma limpeza operacional é explicitamente autorizada
- **THEN** o inventário continua fechado e agregado, as tabelas técnicas não entram na lista de exclusão e a propriedade e concessões permanecem

### Requirement: Monitor operacional com qualidade explícita
O sistema SHALL apresentar monitor com HTTP, pool, banco, filas, workers, armazenamento, host e incidentes, preservando o card existente. Toda métrica SHALL distinguir origem, instante, escopo e indisponibilidade; dados antigos MUST NOT indicar saúde atual.

#### Scenario: Fonte ausente
- **WHEN** o host não possui fonte configurada ou permitida
- **THEN** o painel mostra a lacuna, preserva as demais fontes e não inventa valores

### Requirement: Coleta agregada persistente e limitada
O sistema SHALL persistir contagens, erros e histogramas de operações fixas em buckets UTC, com retenção configurável e limites de consultas, memória e tempo. Falha do monitor MUST NOT falhar a operação observada. IDs de negócio, URLs completas, SQL, cookies, tokens e textos de exceção MUST NOT ser dimensões ou payloads.

#### Scenario: Telemetria falha
- **WHEN** a persistência ou uma fonte falha
- **THEN** a operação de negócio mantém seu resultado e a cobertura perdida é sinalizada

#### Scenario: Poucas amostras
- **WHEN** não há amostras suficientes para um percentil
- **THEN** o percentil permanece nulo e a contagem amostral é exibida

### Requirement: Histórico e incidentes fundamentados
O sistema SHALL apresentar histórico com janelas limitadas e alertas configuráveis, persistência mínima, deduplicação e recuperação. Ausência de métricas SHALL ser lacuna e MUST NOT ser convertida em indisponibilidade confirmada do produto.

#### Scenario: Pico e recuperação
- **WHEN** um limiar é excedido brevemente ou de forma persistente e depois se recupera
- **THEN** somente a violação persistente ativa incidente e a recuperação fica registrada sem duplicatas

### Requirement: Relatório técnico sanitizado
O sistema SHALL exportar JSON e texto por intervalo autorizado de até 24 horas, com limite de tamanho, métricas, fontes, versão, ambiente, séries e lacunas. Relatórios MUST NOT incluir árvore, dados pessoais ou conteúdo de domínio.

#### Scenario: Exportação autorizada
- **WHEN** o administrador tem metrics e export
- **THEN** recebe relatório limitado e auditado, com incidentes somente se também tem incidents

### Requirement: Integração de host explícita
O sistema SHALL aceitar somente snapshot de host numérico de schema fechado, fonte, UTC e idade verificáveis, separando filesystem real de bytes cadastrados e de quotas OCI. Configuração ausente ou sem permissão SHALL ser declarada. A integração MUST NOT instalar agentes ou alterar infraestrutura automaticamente.

#### Scenario: Snapshot inválido ou antigo
- **WHEN** a fonte está inválida, futura ou envelhecida
- **THEN** os dados não são tratados como medidas atuais nem usados para declarar saúde
