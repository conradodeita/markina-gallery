# Spec Delta

## ADDED Requirements

### Requirement: Operação de backup restrita ao proprietário
A consulta e as ações do backup PostgreSQL SHALL estar disponíveis somente ao `PlatformOwner` autenticado. Iniciar cópia, solicitar verificação ou preparar recuperação SHALL exigir a reautenticação vigente para ações sensíveis e SHALL registrar ator, ação, instante e resultado em auditoria sem incluir dump, chave ou credencial.

#### Scenario: Fotógrafo ou sessão sem reautenticação
- **WHEN** uma conta sem papel de proprietário ou sessão sem reautenticação tenta operar o backup
- **THEN** o servidor recusa a ação, preserva o destino e registra somente o resultado sanitizado

#### Scenario: Proprietário inicia uma cópia
- **WHEN** o proprietário autenticado confirma a ação após reautenticação
- **THEN** o servidor agenda somente a operação fixa de cópia global e registra a ação na auditoria

### Requirement: Estado de backup sanitizado e sem consulta remota na leitura
A página SHALL apresentar o último estado persistido como atual, desatualizado, indisponível ou desconhecido. Uma leitura comum da página MUST NOT iniciar backup nem consultar o destino remoto.

#### Scenario: Destino indisponível ou estado antigo
- **WHEN** a última coleta falhou, está vencida ou não existe
- **THEN** a interface distingue indisponível, desatualizado ou desconhecido e não afirma que o backup está saudável

### Requirement: Ações de backup com escopo fechado
A interface SHALL oferecer somente ações de cópia, validação e preparação de recuperação definidas pelo sistema. Usuários MUST NOT fornecer executável, comando, remote, caminho arbitrário ou segredo por formulário ou parâmetro da ação.

#### Scenario: Tentativa de alterar o escopo da operação
- **WHEN** uma requisição contém remote, caminho, opção ou segredo fora do contrato fixo
- **THEN** o backend recusa a operação sem executar subprocesso ou transmitir conteúdo

### Requirement: Configuração não secreta do ciclo
A UI SHALL permitir somente configurar cadência e retenção previamente aprovadas, com validação, reautenticação e auditoria. Credenciais do destino e chave/senha Restic MUST NOT ser digitadas, exibidas ou armazenadas pela UI.

#### Scenario: Política ainda não aprovada
- **WHEN** não existe política de retenção aprovada
- **THEN** a UI mantém a retenção automática desativada e não oferece uma escolha implícita

#### Scenario: Tentativa de configurar segredo ou destino arbitrário
- **WHEN** uma requisição inclui chave, senha, token, remote ou caminho de destino
- **THEN** o backend recusa a alteração e não registra o valor recebido

### Requirement: Recuperação visível sem promoção implícita
A interface SHALL mostrar origem, alvo isolado, resultado de verificação e estado da recuperação. Ela MUST NOT substituir o banco ativo por uma ação comum da UI; promoção continua condicionada ao gate operacional específico.

#### Scenario: Recuperação isolada concluída
- **WHEN** a restauração isolada termina
- **THEN** a interface mostra a evidência sanitizada e mantém o banco ativo sem alteração até a autorização operacional correspondente
