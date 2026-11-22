## ADDED Requirements

### Requirement: Publicação pontual protegida de Orders
O operador SHALL atualizar somente o piloto Orders 0088→0089 com inventário somente leitura, preparação isolada e aplicação explicitamente aprovada. MUST preservar os gates existentes e MUST NOT iniciar deploy automático. A origem SHALL ser `https://markina.pickyourpic.com.br`, Nginx loopback 8080 e projeto `markina-gallery`.

#### Scenario: Baseline publicado do piloto
- **WHEN** o preflight confere a atualização
- **THEN** ele exige checkout `9bd66c48d7d43462886652b8fe85fdcbff877f64`, schema 0088 e identidade existente antes de preparar o destino 0089

#### Scenario: Aprovação da janela
- **WHEN** o proprietário aceita a interrupção temporária apresentada em 25/10/2026
- **THEN** a preparação e os ensaios do procedimento podem avançar; a aplicação continua condicionada a candidato, CI, backup/recuperação e inventário verificáveis

### Requirement: Preparação sem substituir runtime
A preparação SHALL construir candidatos imutáveis usando as bases ativas, preservar exatamente as distribuições Python com mercadopago 3.6.0 já instalado e compilar o frontend com Node ativo e lockfile. Preparação MUST NOT alterar containers ativos, checkout, configuração ou credenciais existentes.

#### Scenario: Falha de ensaio
- **WHEN** build, comparação de distribuições, restauração, cifragem ou preservação falha
- **THEN** o candidato não é liberado para aplicação e os serviços operacionais continuam intactos

### Requirement: Restauração isolada antes da janela
O operador SHALL ensaiar backup/restore, cifragem, preservação financeira e migration em PostgreSQL descartável sem saída externa. Artefatos com dados/chaves SHALL permanecer fora do Git, no host, em diretório protegido e arquivos 0600.

#### Scenario: Ensaio com dados operacionais
- **WHEN** o backup é restaurado para validar a cadeia 0088→0089
- **THEN** o destino não possui portas públicas nem canais externos, o cofre é validado sem divulgar valores e os registros operacionais não são alterados

### Requirement: Interrupção verificável dos escritores Orders
A aplicação SHALL usar lock compartilhado e fingerprint atual. API/web/worker geral SHALL parar por SIGTERM, sem SIGKILL. Os seis workers especializados SHALL conservar imagens/configurações; legados MAY receber SIGINT somente por opt-in, identidade conferida e filas quiescentes. Todos os escritores SHALL estar parados antes de 0089.

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
- **THEN** a recuperação SHALL confirmar schema 0088, respeitar sinais já solicitados e retomar os mesmos containers anteriores, sem depender de consulta externa de CI ou aceitar um processo ainda terminando como recuperado

### Requirement: Recuperação conservadora e isolamento do ensaio
A aplicação SHALL aceitar somente schema 0088 e aplicar somente 0089, comparar evidência financeira/PIX/Orders e conferir SHA, imagens e saúde. O cofre existente SHALL servir API/worker sem rotação e com APP_ENV preservado. Depois de iniciar DDL, falha MUST preservar manutenção/evidências e exigir recuperação compatível.

#### Scenario: Falha depois de iniciar DDL
- **WHEN** migration ou verificação posterior falha
- **THEN** o procedimento não volta automaticamente ao binário 0088 e não apaga ou reescreve tentativas financeiras

### Requirement: Emissão fechada e ensaio do proprietário
Cobranças reais MUST permanecer bloqueadas. Teste SHALL aceitar somente o par tenant/cliente do proprietário verificado. Retirar esse par SHALL fechar emissão mantendo receiver/conciliação dos registros existentes.

#### Scenario: Outros clientes e projetos
- **WHEN** o ensaio é publicado
- **THEN** outros clientes não recebem nem conseguem emitir com a conta de teste; PIX permanece disponível e serviços externos ao escopo não são parados/recriados

### Requirement: Preservar a correção Pillow já publicada
O piloto Orders SHALL exigir os seis IDs corrigidos e o recibo Pillow aprovado, incluir seu overlay persistente no inventário/Compose e preservar os mesmos containers/imagens. Preparação, backup e fingerprint Orders SHALL ser renovados após essa publicação, sem reaproveitar o recibo anterior.

#### Scenario: Tentativa de retornar a um especializado antigo
- **WHEN** imagem ativa, recibo ou overlay Pillow diverge da publicação aprovada
- **THEN** o preflight recusa antes de manutenção, migration ou troca de serviço

#### Scenario: Recarga nginx ainda em propagação
- **WHEN** a configuração original é restaurada depois da janela
- **THEN** a saúde pública SHALL ser confirmada com espera limitada antes de remover o journal, mantendo falha e recuperação para503 persistente

### Requirement: Snapshot Orders reconciliado permanece congelado
O gate de fonte SHALL manter igualdade estrita em backend/frontend/docker com `b69a95c526912d725863a57a13f8735a62f671ed`, que inclui os ajustes revisados de mínimo, processamento e compras simultâneas. Os seis processos Pillow13 já publicados SHALL conservar as imagens e o overlay aprovados.

#### Scenario: Outra alteração de runtime depois da reconciliação
- **WHEN** a preparação ou selagem encontra diferença adicional em backend/frontend/docker
- **THEN** o procedimento recusa sem ampliar allowlist ou publicar o candidato

### Requirement: Preflight Orders somente leitura por SSH restrito
O acesso remoto para atualizar o inventário Orders SHALL aceitar somente um comando forçado com SHA completo da `main`, script imutável conferido por blob Git e modo fixo de inventário. SHALL usar exclusivamente a credencial dedicada `production-preflight`; SHALL NOT permitir shell, stdin arbitrário, argumentos remotos, modo prepare/apply, credenciais de deploy ou escrita no checkout.

#### Scenario: Preflight Orders autorizado
- **WHEN** o operador dispara o workflow manual na `main` com a operação `orders-pilot-inventory`
- **THEN** o job envia somente `MARKINA_ORDERS_TARGET_SHA=<SHA completo>`, o wrapper verifica o blob aprovado e executa somente `inventory`; o helper confirma que o SHA ainda é a ponta da `main` e emite o inventário minimizado/fingerprint

#### Scenario: Comando, SHA ou blob divergente
- **WHEN** o cliente envia comando diferente, SHA malformado/desatualizado ou o conteúdo baixado diverge do blob fixado
- **THEN** o wrapper falha fechado antes de executar Python ou consultar serviços

#### Scenario: Aplicação ou credencial mutável
- **WHEN** alguém tenta usar o canal preflight para executar `prepare`, `apply`, shell ou credenciais de deploy
- **THEN** a rota rejeita a operação e não inicia alteração remota

#### Scenario: Contrato CLI do wrapper com o helper
- **WHEN** o wrapper encaminha a execução Python para o helper Orders
- **THEN** os argumentos fixos `inventory --sha <SHA completo>` SHALL ser aceitos pelo parser real do helper; o teste de contrato SHALL exercer essa fronteira com acesso ao host simulado, antes da instalação operacional

### Requirement: Preservar o piloto Orders existente
O inventário SHALL validar identidade publicada, imagens, overlay e restrição ao mesmo par proprietário, com cobranças reais bloqueadas. A preparação SHALL preservar uma cópia da identidade anterior. Sua substituição SHALL ocorrer atomicamente apenas depois da confirmação do novo runtime.

#### Scenario: Identidade existente divergente
- **WHEN** a identidade, imagens, overlay, par permitido ou schema divergem do piloto publicado inventariado
- **THEN** o procedimento recusa antes de manutenção e DDL; não aceita o inventário histórico 0087 nem sobrescreve uma identidade sem sua cópia de recuperação

### Requirement: Preservação financeira na atualização Orders
A preparação SHALL ensaiar a migration sobre o backup atual com as quatro tabelas Orders existentes. As comparações financeiras SHALL incluir registros completos de Orders, configurações cifradas e todas as referências financeiras legadas, sem divulgar valores ou identificadores de clientes.

#### Scenario: Pagamento anterior em processamento
- **WHEN** a atualização encontra tentativas Orders pendentes, aprovadas ou recusadas
- **THEN** ela preserva integralmente os registros, IDs, snapshots e estados; a migration altera somente a unicidade de tentativas ativas por revisão e a conciliação retoma com o novo worker

### Requirement: Validação proporcional do piloto sandbox
O piloto restrito ao cliente do proprietário SHALL usar validação proporcional: CI aplicável, checks focados no delta, preservação/recuperação da migration e smoke de publicação. Baterias rígidas adicionais, ampliação opcional de suíte e repetição sem mudança relevante SHALL NOT bloquear o deploy. Evidências ainda válidas MAY ser reaproveitadas. O acompanhamento manual do proprietário SHALL ser aceito para os cenários visuais/funcionais do sandbox.

#### Scenario: Componente inalterado e evidência válida
- **WHEN** não há mudança relevante no componente, dependência ou contrato já validado
- **THEN** o executor reaproveita as evidências aplicáveis e não inicia outra bateria integral, teste de carga, calibração ou ensaio opcional para condicionar a publicação do piloto

#### Scenario: Alteração de índice sobre tentativas existentes
- **WHEN** a atualização aplica 0089 ao piloto 0088
- **THEN** a validação essencial comprova backup recuperável, preservação das tentativas/referências e saúde/isolamento após a publicação, sem exigir uma nova homologação separada ou testes de cobranças reais

### Requirement: Continuidade e rapidez da publicação autorizada
O executor SHALL consolidar correções relacionadas no candidato atual e priorizar o deploy após seus gates essenciais. SHALL NOT criar sucessivas rodadas de push/CI apenas por testes opcionais ou atualização documental. Enquanto houver CI pendente, SHALL acompanhar a cada 30 minutos. A autorização explícita de merge e deploy deste piloto SHALL persistir durante a ausência do proprietário, sem nova confirmação do mesmo escopo.

#### Scenario: CI pendente durante ausência do proprietário
- **WHEN** o proprietário deixa autorizado merge/deploy e pede acompanhamento agendado
- **THEN** o executor verifica o CI a cada 30 minutos, continua após sucesso e informa conclusão ou impedimento real; não encerra a missão apenas porque está esperando o CI nem repete mensagens sem mudança

#### Scenario: Preparação recuperável e candidato aprovado
- **WHEN** o CI aplicável passa e o inventário/backup/plano de recuperação estão conferidos
- **THEN** o executor apresenta o inventário, portas/serviços e plano na conversa e aplica a atualização já autorizada, mantendo Mercado Pago sandbox, cobranças reais bloqueadas e o mesmo cliente permitido
