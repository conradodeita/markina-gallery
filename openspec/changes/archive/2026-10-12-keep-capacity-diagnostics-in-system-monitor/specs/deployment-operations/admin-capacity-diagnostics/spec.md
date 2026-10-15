# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Diagnóstico sob demanda na Visão geral`
- TO: `### Requirement: Diagnóstico sob demanda no Monitor do Sistema`

## MODIFIED Requirements

### Requirement: Diagnóstico sob demanda no Monitor do Sistema

O Monitor do Sistema SHALL apresentar seção recolhível “Diagnóstico de capacidade”, inicialmente fechada, usando os componentes e estados acessíveis existentes. Ao abrir, SHALL consultar o endpoint dedicado, mostrar escopo/UTC/classificação junto aos valores, cobertura das filas e orçamento incompleto; atualização SHALL ser manual, sem polling automático ou persistência no navegador. Falha diagnóstica SHALL manter utilizável o restante do painel. O painel SHALL explicar que esta é uma leitura parcial de capacidade, sem semáforo de expansão ou cumprimento de SLO geral.

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

O Monitor do Sistema SHALL oferecer a ação explícita **Copiar relatório** somente enquanto existir um snapshot de capacidade válido e autorizado na tela. A ação SHALL produzir texto UTF-8 em formato versionado, determinístico e legível, usando exclusivamente os campos permitidos do mesmo snapshot exibido e sem iniciar nova coleta. O relatório SHALL incluir versão do formato e do contrato, janela UTC da coleta, uso de cache, escopos, pool, conexões PostgreSQL, as cinco classes de fila, orçamento global, cobertura e limitações. Para cada métrica, SHALL preservar valor, unidade, fonte, escopo, instante UTC, classe de evidência e motivo de indisponibilidade; valor desconhecido MUST NOT ser omitido, convertido em zero ou apresentado como observado.

A geração e a cópia SHALL ocorrer somente no navegador após gesto explícito do administrador, sem endpoint novo, persistência, histórico, download ou transmissão automática. O serializador SHALL usar allowlist fechada e MUST NOT copiar campos desconhecidos nem incluir SQL, banco, usuário, host, IP, DSN, caminho, identificador de negócio, nome pessoal, telefone, foto, token, conteúdo de mensagem ou biometria. A interface SHALL comunicar de forma acessível o sucesso ou a falha da operação; falha da área de transferência SHALL preservar o snapshot e MUST NOT ser confundida com falha da coleta.

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
