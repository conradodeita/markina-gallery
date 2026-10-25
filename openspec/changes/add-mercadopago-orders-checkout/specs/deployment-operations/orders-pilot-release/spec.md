## ADDED Requirements

### Requirement: Publicação pontual protegida de Orders
O operador SHALL dispor de procedimento específico para o primeiro release Orders, com inventário somente leitura, preparação isolada e aplicação explicitamente aprovada. O procedimento MUST preservar os gates API/web, facial e InfinitePay existentes e MUST NOT iniciar deploy automático. A origem SHALL permanecer `https://markina.pickyourpic.com.br`, Nginx loopback 8080 e projeto `markina-gallery`.

#### Scenario: Aprovação da janela
- **WHEN** o proprietário aceita a interrupção temporária apresentada em 25/10/2026
- **THEN** a preparação e os ensaios do procedimento podem avançar; a aplicação continua condicionada a candidato, CI, backup/recuperação e inventário verificáveis

### Requirement: Preparação sem substituir runtime
A preparação SHALL construir candidatos imutáveis usando as bases ativas, adicionar somente mercadopago 3.6.0 às distribuições Python e compilar o frontend com Node ativo e lockfile. Preparação MUST NOT alterar containers ativos, checkout, configuração ou credenciais existentes.

#### Scenario: Falha de ensaio
- **WHEN** build, comparação de distribuições, restauração, cifragem ou preservação falha
- **THEN** o candidato não é liberado para aplicação e os serviços operacionais continuam intactos

### Requirement: Restauração isolada antes da janela
O operador SHALL ensaiar backup/restore, cifragem, preservação financeira e migration em PostgreSQL descartável sem saída externa. Artefatos com dados/chaves SHALL permanecer fora do Git, no host, em diretório protegido e arquivos 0600.

#### Scenario: Ensaio com dados operacionais
- **WHEN** o backup é restaurado para validar a cadeia 0087→0088
- **THEN** o destino não possui portas públicas nem canais externos, o cofre é validado sem divulgar valores e os registros operacionais não são alterados

### Requirement: Interrupção verificável dos escritores Orders
A aplicação SHALL usar lock compartilhado e fingerprint atual. API/web/worker geral SHALL parar por SIGTERM, sem SIGKILL. Os seis workers especializados SHALL conservar imagens/configurações; legados MAY receber SIGINT somente por opt-in, identidade conferida e filas quiescentes. Todos os escritores SHALL estar parados antes de 0088.

#### Scenario: Worker não confirma parada
- **WHEN** o timeout expira, o código de saída diverge ou aparece trabalho ativo
- **THEN** a migration não inicia e os mesmos containers anteriores são retomados sem reclassificar mensagens ou apagar filas

#### Scenario: Reinício automático dos legados
- **WHEN** o inventário confirma `unless-stopped` nos seis workers especializados
- **THEN** o procedimento SHALL registrar e suspender temporariamente essa política antes do sinal, impedir reinício durante DDL e restaurar a mesma política ao retomar os mesmos containers; alteração inesperada MUST bloquear a operação

#### Scenario: Resultado de mensagem desconhecido
- **WHEN** há mensagens históricas em `unknown`
- **THEN** o procedimento MUST preservar seus registros e MUST NOT reenviá-las ou classificá-las como concluídas para liberar o gate

#### Scenario: Executor interrompido antes de DDL
- **WHEN** a conexão/executor é interrompida durante a janela e o journal registra schema ainda não iniciado
- **THEN** a recuperação SHALL confirmar schema 0087, respeitar sinais já solicitados e retomar os mesmos containers anteriores, sem depender de consulta externa de CI ou aceitar um processo ainda terminando como recuperado

### Requirement: Recuperação conservadora e isolamento do ensaio
A aplicação SHALL aceitar somente schema 0087 e aplicar somente 0088, comparar evidência financeira/PIX e conferir SHA, imagens e saúde. O cofre existente SHALL servir API/worker sem rotação e com APP_ENV preservado. Depois de iniciar DDL, falha MUST preservar manutenção/evidências e exigir recuperação compatível.

#### Scenario: Falha depois de iniciar DDL
- **WHEN** migration ou verificação posterior falha
- **THEN** o procedimento não volta ao binário 0087 e não apaga ou reescreve tentativas financeiras

### Requirement: Emissão fechada e ensaio do proprietário
Cobranças reais MUST permanecer bloqueadas. Teste SHALL aceitar somente o par tenant/cliente do proprietário verificado. Retirar esse par SHALL fechar emissão mantendo receiver/conciliação dos registros existentes.

#### Scenario: Outros clientes e projetos
- **WHEN** o ensaio é publicado
- **THEN** outros clientes não recebem nem conseguem emitir com a conta de teste; PIX permanece disponível e serviços externos ao escopo não são parados/recriados
