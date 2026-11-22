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

Cada valor SHALL informar unidade, fonte sanitizada, UTC e escopo (processo respondente, banco atual ou PostgreSQL conectado). O contrato SHALL classificar valores como `observed`, `calculated`, `estimated` ou `unavailable`, com motivo. A resposta SHALL registrar intervalo UTC, versão, cobertura e lacunas, sem alegar snapshot atômico. Só contagem vazia observada é zero; falta de acesso/evidência MUST NOT virar zero ou sucesso.

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

O diagnóstico SHALL mostrar conexões agregadas do banco atual e do PostgreSQL conectado, estados conhecidos/desconhecidos, `max_connections` e reservas legíveis. O pool SHALL informar classe, limites base/overflow, timeout e ocupação observável apenas da API respondente. Limites MUST NOT virar conexões abertas nem ser somados/multiplicados; pool ilimitado não recebe teto inventado. Espera/timeouts sem instrumentação ficam indisponíveis.

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

O sistema SHALL separar conexões observadas de orçamento potencial. Orçamento global exige inventário vigente de processos, engines/pools, tarefas pontuais concorrentes, consumidores externos e reservas, com origem, escopo e UTC. Sem cobertura completa, orçamento e margem SHALL ser `unavailable`, com lacunas declaradas; o painel MUST NOT recomendar workers, expansão ou capacidade segura de usuários. A documentação SHALL evitar dupla contagem de reservas e pools compartilhados.

#### Scenario: Conhece somente API e configuração versionada
- **WHEN** há medição do pool respondente e descrição de serviços no repositório, mas não inventário de processos ativos, pools e reservas
- **THEN** o orçamento permanece indisponível, sem assumir uma réplica por serviço ou reutilizar números de benchmark como medições atuais

#### Scenario: Há diferença positiva entre limite e conexões observadas
- **WHEN** o PostgreSQL apresenta menos conexões que seu limite configurado
- **THEN** o diagnóstico não converte a diferença em margem orçada nem em autorização para novos workers

### Requirement: Filas duráveis com cobertura e semântica de espera delimitadas

O diagnóstico SHALL separar filas de mídia, ajuste de prévias, busca, indexação e manutenção facial, com contagens aguardando/em processamento e idade/espera quando evidenciadas. Agendamentos futuros/vencidos ficam distintos; processamento não conta como espera; lease vencido aparece como recuperável sem ação. Dependências conhecidas distinguem bruto de elegível; sem evidência, elegibilidade/espera fica indisponível.

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

### Requirement: Cobertura e limites do diagnóstico de filas

A cobertura SHALL declarar outboxes/mensagens e rotinas não incluídas, sem total geral. Redis de sinalização MUST NOT ser autoridade de jobs. O snapshot SHALL NOT afirmar worker ativo, tempo até conclusão, throughput, p95 ou SLO geral.

#### Scenario: Rotinas fora do diagnóstico

- **WHEN** existem outboxes ou outras rotinas não incluídas nas classes consultadas
- **THEN** a cobertura as identifica sem agregá-las a um total geral de filas

### Requirement: Coleta limitada e saída sanitizada sem efeitos no domínio

Coleta SHALL ser read-only, usar agregações com limites de tempo/cardinalidade e MUST NOT carregar históricos ou payloads. Respostas/logs/erros SHALL usar allowlist e categorias sanitizadas, sem SQL, banco/usuário/host, IP, DSN, caminhos, IDs comerciais, nomes, telefones, fotos, tokens, mensagens ou biometria. Não alterar defaults, pools, `.env`, privilégios, limites, réplicas, filas ou infraestrutura; sem claims, locks, reprocessamento ou envio.

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

### Requirement: Diagnóstico sob demanda no Monitor do Sistema

O Monitor SHALL mostrar seção recolhível `Diagnóstico de capacidade`, fechada inicialmente, e consultar endpoint dedicado ao abrir. Deve exibir escopo/UTC/classificação, cobertura e orçamento incompleto. Atualização é manual, sem polling ou persistência no navegador. Falha não bloqueia o painel; a interface explica que a leitura é parcial e não atesta expansão ou SLO geral.

#### Scenario: Abertura e atualização
- **WHEN** o administrador abre a seção e depois solicita atualização
- **THEN** vê carregamento, resultado com data da coleta e eventuais lacunas, sem requisição duplicada enquanto há outra em andamento e sem polling ao recolher a seção

#### Scenario: Falha parcial
- **WHEN** PostgreSQL ou uma classe de fila está indisponível, mas outras informações foram coletadas
- **THEN** a seção apresenta cada estado corretamente e o restante do Monitor do Sistema continua operacional

#### Scenario: Sessão perde autorização
- **WHEN** uma atualização recebe acesso negado ou o contexto administrativo é encerrado
- **THEN** a interface retira o snapshot exibido e segue o tratamento de autenticação existente, sem mostrar dados antigos como disponíveis


#### Scenario: Visão Geral sem duplicação
- **WHEN** o proprietário abre a Visão Geral administrativa
- **THEN** o card Capacidade e filas não aparece e essa página não consulta capability ou snapshot do diagnóstico

### Requirement: Relatório sanitizado copiável do snapshot atual

O Monitor SHALL oferecer `Copiar relatório` somente com snapshot válido e autorizado exibido. Um gesto explícito SHALL copiar texto UTF-8 determinístico e versionado daquele snapshot, sem nova coleta. O relatório inclui versão, janela UTC, cache, escopos, pool/conexões, cinco filas, orçamento, cobertura e limites. Cada métrica preserva valor/unidade/fonte/escopo/UTC/classe/motivo; valor desconhecido MUST NOT ser omitido, virar zero ou ser observado.

#### Scenario: Administrador copia o snapshot exibido
- **WHEN** existe um snapshot autorizado na tela e o administrador aciona **Copiar relatório**
- **THEN** o navegador recebe uma única representação textual desse mesmo snapshot, sem nova requisição ao endpoint e com retorno acessível de sucesso

#### Scenario: Relatório preserva evidência e lacunas
- **WHEN** o snapshot contém zero observado, valor calculado ou estimado e valor indisponível com motivo
- **THEN** o relatório conserva cada uma dessas classificações, seus valores ou nulidade, unidades, fontes, escopos e horários, além da cobertura e das limitações, sem promover lacuna a fato

#### Scenario: Serialização ignora campo não permitido
- **WHEN** o objeto recebido contém campo adicional fora do contrato permitido
- **THEN** o relatório não inclui esse campo e mantém somente a projeção sanitizada definida para o formato versionado

#### Scenario: Área de transferência indisponível
- **WHEN** a API de área de transferência não está disponível ou rejeita a escrita
- **THEN** a interface informa que não foi possível copiar, mantém o snapshot visível e não dispara atualização, download ou envio alternativo

#### Scenario: Snapshot deixa de estar autorizado
- **WHEN** uma atualização falha por perda de autorização e a interface remove o snapshot
- **THEN** a ação de copiar deixa de estar disponível e nenhum relatório anterior permanece acessível pela interface

### Requirement: Cópia e comunicação do relatório

A geração e cópia SHALL ocorrer no navegador após gesto explícito, sem endpoint novo, persistência, histórico, download ou transmissão. A interface SHALL comunicar sucesso/falha de forma acessível; falha de clipboard preserva snapshot e MUST NOT ser confundida com falha de coleta.

#### Scenario: Cópia local do snapshot autorizado

- **WHEN** o administrador copia relatório de snapshot válido na tela
- **THEN** o navegador copia o texto sem transmitir ou persistir o conteúdo

### Requirement: Allowlist do relatório de capacidade

O serializador SHALL usar allowlist fechada e MUST NOT copiar campos desconhecidos nem dados técnicos ou pessoais, incluindo SQL, banco, usuário, host, IP, DSN, caminho, identificadores comerciais, nomes, telefones, fotos, tokens, mensagens e biometria.

#### Scenario: Campo adicional ou dado proibido

- **WHEN** o snapshot contém campo desconhecido ou informação técnica/pessoal fora da allowlist
- **THEN** o relatório omite esses dados

### Requirement: Diagnósticos operacionais restritos à conta proprietária
O backend SHALL exigir proprietário por UUID, sessão/vínculo válidos e installation_operator para capacidade e observabilidade facial. Propriedade SHALL ser revalidada antes/depois da coleta e na entrega de cache. Capabilities SHALL ocultar acesso de outros administradores. A regra MUST NOT depender de e-mail fixo. Contrato métrico, limites e card SHALL ser preservados.

#### Scenario: Operador antigo não proprietário
- **WHEN** outro administrador possui installation_operator mas não o UUID proprietário
- **THEN** capabilities indicam ausência de acesso e o backend recusa a consulta antes da coleta

#### Scenario: Proprietário troca e-mail
- **WHEN** a conta proprietária troca e verifica o novo e-mail, mantendo UUID, sessão/vínculo e concessão válidos
- **THEN** continua acessando diagnóstico, sem transferir acesso a outra conta que use o e-mail anterior

### Requirement: Dica de interpretação do diagnóstico de capacidade
O card de capacidade SHALL oferecer dica acessível por toque/teclado que explique leitura pontual das conexões e filas, atualização manual e possibilidade de copiar o relatório para suporte. A dica SHALL informar que esse snapshot não determina capacidade máxima e não altera autorização, coleta ou serialização existentes.

#### Scenario: Proprietário consulta a dica
- **WHEN** o proprietário abre a ajuda do card de capacidade
- **THEN** recebe a explicação em linguagem simples, mantendo as ações Consultar diagnóstico e Copiar relatório e seus contratos existentes
