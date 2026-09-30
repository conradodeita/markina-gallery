# admin-capacity-diagnostics Specification

## Purpose

Permitir ao administrador da instalação única consultar um diagnóstico agregado e somente leitura das conexões, dos pools e das filas cobertas, distinguindo evidência disponível, estimativas e lacunas antes de decisões de capacidade.

## Requirements

### Requirement: Diagnóstico exclusivo do administrador da instalação única

O sistema SHALL fornecer `GET /admin/capacity-observability` somente para sessão administrativa válida, com vínculo ativo revalidado à conta única ativa da instalação. O sistema MUST preservar os guardas de ownership e recusar contexto ausente, suspenso ou múltiplo, inclusive antes de entregar dados em cache. Identificadores externos de conta SHALL NOT selecionar o escopo do diagnóstico.

#### Scenario: Administrador autorizado
- **WHEN** um administrador vinculado à conta única ativa solicita o diagnóstico
- **THEN** recebe somente o diagnóstico agregado da instalação atual, sem opções de outras contas

#### Scenario: Cliente ou visitante tenta consultar
- **WHEN** a requisição não possui sessão administrativa válida, inclusive quando possui sessão cliente válida
- **THEN** o acesso é negado sem devolver métricas ou iniciar coleta diagnóstica

#### Scenario: Contexto revogado ou inválido
- **WHEN** o vínculo é revogado, a conta é suspensa ou a instalação deixa de conter exatamente uma conta
- **THEN** a próxima requisição é recusada mesmo que exista snapshot anterior em cache, sem fallback para outra conta

### Requirement: Evidência e escopo explícitos em cada valor

Cada valor SHALL informar unidade, fonte sanitizada, instante de coleta em UTC e escopo entre processo respondente, banco atual e servidor PostgreSQL conectado. O contrato SHALL distinguir `observed` (observado diretamente), `calculated` (calculado de fontes explícitas), `estimated` (aproximação identificada) e `unavailable` (indisponível com motivo e valor nulo). A resposta SHALL informar início/fim da coleta, versão do contrato, cobertura e lacunas; SHALL NOT alegar simultaneidade atômica entre as fontes. Uma contagem vazia observada SHALL ser zero; falta de acesso ou de evidência MUST NOT ser substituída por zero ou sucesso.

#### Scenario: Snapshot reutilizado
- **WHEN** a resposta reutiliza dados coletados anteriormente
- **THEN** conserva os instantes UTC originais e identifica o uso do cache, sem apresentar o instante da requisição como nova medição

#### Scenario: Fonte indisponível
- **WHEN** uma consulta falha por permissão, timeout ou recurso não suportado após autorização válida
- **THEN** somente os valores afetados ficam nulos e indisponíveis com motivo sanitizado, preservando as demais seções válidas

#### Scenario: Idade calculada sem histórico de espera
- **WHEN** existe timestamp do registro, mas não existe histórico confiável de entrada/saída da fila
- **THEN** a idade do registro é identificada como cálculo e qualquer uso como espera é identificado como estimativa, sem inventar duração de serviço ou percentil

### Requirement: Conexões PostgreSQL e pool com fronteiras verificáveis

O diagnóstico SHALL mostrar contagens agregadas de conexões cliente do banco atual e do servidor PostgreSQL conectado, separando estados conhecidos e desconhecidos, além de `max_connections` e reservas técnicas quando legíveis. O diagnóstico SHALL mostrar classe, limite base, overflow máximo, timeout de aquisição e ocupação observável somente do pool do processo API respondente. Limites configurados MUST NOT ser apresentados como conexões abertas, e contadores de processo MUST NOT ser multiplicados ou somados como uso global. Pools ilimitados ou sem semântica compatível SHALL ser identificados sem inventar teto finito. Espera real de aquisição e número de timeouts SHALL permanecer indisponíveis quando não instrumentados.

#### Scenario: Pool com capacidade ociosa
- **WHEN** o pool local tem teto finito superior à sua ocupação observada
- **THEN** o sistema distingue teto potencial, conexões em uso e ociosas, sem afirmar que todo o teto está conectado ao banco

#### Scenario: Réplicas não inventariadas
- **WHEN** a API não conhece quantidade e configuração dos outros processos
- **THEN** apresenta o pool como processo respondente e não infere ocupação de workers nem total de conexões da aplicação a partir dele

#### Scenario: Visibilidade parcial ou banco não PostgreSQL
- **WHEN** estados de conexões estão ocultos ou uma função PostgreSQL não está disponível no ambiente
- **THEN** explicita estados desconhecidos ou valores indisponíveis, sem assumir que há zero conexões e sem conceder privilégios ou alterar o banco

### Requirement: Orçamento global dependente de inventário completo

O sistema SHALL separar conexões observadas de orçamento potencial. Um orçamento global exige inventário explícito e vigente de todos os processos, engines/pools, concorrências de tarefas pontuais, consumidores externos do mesmo servidor e reservas técnicas/operacionais, com origem, escopo e UTC. Neste recorte, sem uma fonte completa desse inventário, a resposta SHALL informar `unavailable` para orçamento global e margem orçada, listando lacunas; o painel MUST NOT recomendar quantidade segura de workers, expansão ou capacidade de usuários. A documentação SHALL explicar como evitar dupla contagem de reservas e de pools compartilhados pelo mesmo processo.

#### Scenario: Conhece somente API e configuração versionada
- **WHEN** há medição do pool respondente e descrição de serviços no repositório, mas não inventário de processos ativos, pools e reservas
- **THEN** o orçamento permanece indisponível, sem assumir uma réplica por serviço ou reutilizar números de benchmark como medições atuais

#### Scenario: Há diferença positiva entre limite e conexões observadas
- **WHEN** o PostgreSQL apresenta menos conexões que seu limite configurado
- **THEN** o diagnóstico não converte a diferença em margem orçada nem em autorização para novos workers

### Requirement: Filas duráveis com cobertura e semântica de espera delimitadas

O diagnóstico SHALL cobrir separadamente mídia, ajuste de prévias, busca facial, indexação facial e manutenção facial. Para cada classe SHALL apresentar contagens de registros aguardando e em processamento, idade da pendência mais antiga quando fundamentada e classificação da aproximação de espera. O sistema SHALL separar trabalhos agendados para o futuro dos aguardando com agendamento vencido quando houver esse dado; itens em processamento MUST NOT integrar a espera de itens ainda aguardando. Uma recuperação possível de lease vencido SHALL ser contagem separada, sem executar recuperação. Quando houver bloqueio por dependência conhecido, a contagem bruta SHALL ser distinguida dos candidatos após esse filtro. Sem evidência suficiente, elegibilidade ou tempo exato de espera SHALL ficar indisponível.

A cobertura SHALL declarar mensagens/outboxes e outras rotinas não incluídas, sem exibir total geral de todas as filas ou de trabalhos de negócio. Redis de sinalização MUST NOT ser tratado como autoridade de jobs. Nenhuma métrica SHALL afirmar worker ativo, tempo até conclusão, throughput, p95 ou SLO geral a partir desse snapshot.

#### Scenario: Busca agendada e busca em processamento
- **WHEN** há uma busca aguardando com agendamento futuro, outra aguardando com agendamento vencido e uma em processamento
- **THEN** as duas primeiras aparecem em categorias distintas, somente a vencida entra na estimativa dos aguardando aptos pelo agendamento, e a terceira aparece exclusivamente como processamento

#### Scenario: Lease de processamento vencido
- **WHEN** um registro facial em processamento tem lease vencido e agendamento vencido
- **THEN** é contado como processamento recuperável separadamente, sem duplicá-lo na fila aguardando ou alterar lease, tentativas ou estado

#### Scenario: Mídia espera dependência
- **WHEN** um trabalho de mídia aguardando tem análise em estado que bloqueia o claim
- **THEN** entra na contagem bruta e de bloqueados por essa dependência, sem ser apresentado como candidato após o filtro conhecido

#### Scenario: Ajuste sem timestamp de enfileiramento
- **WHEN** a fila de ajuste só dispõe da última atualização do registro
- **THEN** mostra contagem persistida e idade desde atualização como estimativa explícita da espera, mantendo espera exata e elegibilidade completa indisponíveis

#### Scenario: Fila vazia observada
- **WHEN** uma classe foi consultada com sucesso e não tem registros aguardando
- **THEN** mostra contagem zero e ausência de pendência mais antiga, sem converter a ausência em prova de worker saudável

### Requirement: Coleta limitada e saída sanitizada sem efeitos no domínio

A coleta SHALL ser somente leitura, com consultas de agregação restritas, limites explícitos de tempo e cardinalidade, sem carregar históricos inteiros, objetos completos ou payloads de jobs. Resposta, logs diagnósticos e motivos de erro SHALL usar lista fechada de campos e rótulos de baixa cardinalidade. MUST NOT incluir SQL em execução, nomes de banco/usuário/host, IPs, DSNs, caminhos, identificadores de negócio, nomes pessoais, telefones, fotos, tokens, conteúdo de mensagens ou biometria. A operação SHALL preservar defaults, pools, `.env`, privilégios, limites, réplicas, filas e infraestrutura, sem claims, locks de reserva de jobs, reprocessamento ou envio externo.

#### Scenario: Erro contém informação sensível
- **WHEN** o driver ou um registro contém SQL, credencial, caminho ou identificador pessoal em texto livre
- **THEN** esse texto não chega à resposta nem ao log diagnóstico, que usa somente categoria sanitizada

#### Scenario: Coleta excede seu limite
- **WHEN** uma consulta ou a coleta excede o orçamento de execução
- **THEN** a coleta interrompe as etapas afetadas, libera os recursos e indica indisponibilidade, sem prolongar locks ou executar correção operacional

#### Scenario: Requisições repetidas
- **WHEN** o administrador atualiza repetidamente ou abre múltiplas abas
- **THEN** o coletor reutiliza snapshot curto ou sinaliza coleta ocupada dentro do processo, com revalidação de acesso a cada resposta e sem acumular coletas concorrentes ilimitadas

#### Scenario: Leitura preserva filas e contratos existentes
- **WHEN** o diagnóstico é consultado durante jobs pendentes
- **THEN** status, leases, tentativas e configurações permanecem iguais, e os contratos do resumo administrativo e da observabilidade facial existente permanecem compatíveis

### Requirement: Diagnóstico sob demanda na Visão geral

A Visão geral administrativa SHALL apresentar seção recolhível “Diagnóstico de capacidade”, inicialmente fechada, usando os componentes e estados acessíveis existentes. Ao abrir, SHALL consultar o endpoint dedicado, mostrar escopo/UTC/classificação junto aos valores, cobertura das filas e orçamento incompleto; atualização SHALL ser manual, sem polling automático ou persistência no navegador. Falha diagnóstica SHALL manter utilizável o restante do painel. O painel SHALL explicar que esta é uma leitura parcial de capacidade, sem semáforo de expansão ou cumprimento de SLO geral.

#### Scenario: Abertura e atualização
- **WHEN** o administrador abre a seção e depois solicita atualização
- **THEN** vê carregamento, resultado com data da coleta e eventuais lacunas, sem requisição duplicada enquanto há outra em andamento e sem polling ao recolher a seção

#### Scenario: Falha parcial
- **WHEN** PostgreSQL ou uma classe de fila está indisponível, mas outras informações foram coletadas
- **THEN** a seção apresenta cada estado corretamente e o restante da Visão geral continua operacional

#### Scenario: Sessão perde autorização
- **WHEN** uma atualização recebe acesso negado ou o contexto administrativo é encerrado
- **THEN** a interface retira o snapshot exibido e segue o tratamento de autenticação existente, sem mostrar dados antigos como disponíveis
