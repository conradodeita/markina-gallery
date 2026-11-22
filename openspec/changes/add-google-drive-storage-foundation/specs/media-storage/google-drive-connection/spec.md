# media-storage/google-drive-connection Specification

## ADDED Requirements

### Requirement: Autorização controlada pelo proprietário

A conexão Drive SHALL ser autorizada pelo proprietário por fluxo seguro. Senha ou token MUST NOT ser solicitado em mensagem nem gravado em Git, frontend ou log.

#### Scenario: Conexão ainda não autorizada

- **WHEN** uma operação exige Drive e não há autorização válida
- **THEN** a operação permanece bloqueada e apresenta estado indisponível sem simular sucesso

#### Scenario: Início de autorização

- **WHEN** o proprietário autenticado e reautenticado inicia OAuth para o Drive
- **THEN** o servidor usa redirect URI configurada, state aleatório de uso único, PKCE S256 e somente o escopo `drive.file`
- **AND** associa a tentativa à sessão/identidade owner e não expõe client secret ou verifier ao navegador

#### Scenario: Retorno OAuth inválido ou expirado

- **WHEN** callback tem state inválido, tentativa expirada/consumida, sessão trocada, erro Google ou troca de código inválida
- **THEN** nenhuma conexão é ativada e a resposta não revela código, token ou detalhe secreto

#### Scenario: Conexão aceita

- **WHEN** callback Google válido retorna refresh token e escopo mínimo esperado
- **THEN** o servidor persiste somente refresh token cifrado em envelope vinculado ao tenant owner e UUID da credencial, com instante UTC e estado conectado
- **AND** access token, código, state bruto e verifier não são persistidos em claro

#### Scenario: Reautorização sem refresh token

- **WHEN** Google omite refresh token
- **THEN** nova tentativa falha fechada sem substituir a conexão válida anterior

### Requirement: Acesso privado pelo backend

O sistema SHALL executar operações Drive no backend sob tenant e objeto autorizados. MUST NOT gerar links públicos nem permitir navegação de outro tenant.

#### Scenario: Tenant tenta consultar objeto alheio

- **WHEN** uma sessão de tenant solicita metadados ou mídia de objeto pertencente a outro tenant
- **THEN** o servidor nega sem revelar objeto, caminho ou conteúdo

### Requirement: Upload privado e verificável

O backend SHALL enviar arquivos somente por operação interna autorizada, com pasta pai fornecida explicitamente. A sessão MUST NOT ser exposta ao browser, persistida como URL ou registrada em logs. Chamadas reais SHALL exigir `APP_ENV=production`; testes MUST usar transporte sintético sem rede.

#### Scenario: Destino de upload ausente

- **WHEN** a operação de upload recebe pasta pai vazia ou ausente
- **THEN** falha antes de iniciar uma sessão remota
- **AND** não seleciona automaticamente raiz, pasta global ou outro destino

#### Scenario: Sessão de upload aceita

- **WHEN** o Drive retorna URL de sessão para o início de um upload autorizado
- **THEN** o backend aceita somente HTTPS no host e caminho de upload oficiais esperados
- **AND** transmite o stream em chunks retomáveis sem redirecionamento nem repetição automática de POST/PUT
- **AND** mantém a URL somente em memória durante a chamada

### Requirement: Integridade e política de acesso do objeto enviado

O backend SHALL verificar id, nome, MIME, tamanho, pasta pai e MD5 da resposta final. MUST NOT gerar links nem alterar permissões de compartilhamento; o arquivo herda a política da pasta pai. O recibo contém somente ID opaco, tamanho e SHA-256.

#### Scenario: Upload concluído e íntegro

- **WHEN** o Drive confirma a conclusão do upload
- **THEN** o backend compara id, nome, MIME, tamanho, pasta pai e checksum MD5 da resposta com o pedido e os bytes enviados
- **AND** retorna somente identificador opaco, tamanho e checksum SHA-256 local
- **AND** não retorna links públicos, links de navegação ou a URL de sessão
- **AND** não cria permissão ou compartilhamento; visibilidade herdada da pasta deve ser confirmada antes de uso real

#### Scenario: Resposta inesperada ou checksum incompatível

- **WHEN** a URL, protocolo de chunks, status HTTP, metadata final ou checksum não corresponde ao contrato
- **THEN** a operação falha sem sinalizar sucesso ou revelar resposta bruta/credencial
- **AND** não tenta repetir uma operação de escrita automaticamente

### Requirement: Proveniência e disponibilidade da conexão

O sistema SHALL registrar fonte, escopo, instante e disponibilidade observada. Conta, capacidade ou quota não verificadas MUST NOT ser exibidas como confirmadas.

#### Scenario: Persistência da necessidade de reautorização

- **WHEN** a conexão exige `reauthorization_required`
- **THEN** PostgreSQL persiste o estado completo sem truncamento, preservando identidade, envelope e demais dados
- **AND** a ampliação aditiva do campo preserva registros anteriores e seu downgrade recusa reduzir o campo quando houver estados que não cabem no limite antigo

#### Scenario: Estado externo desconhecido

- **WHEN** o último estado é ausente, expirado ou inconclusivo
- **THEN** a interface informa desconhecido ou indisponível e preserva a hora da última evidência válida

#### Scenario: Observação mínima da quota

- **WHEN** o proprietário solicita a quota após conexão OAuth válida
- **THEN** o backend consulta somente os campos `storageQuota(limit,usage)` por conexão TLS e timeout limitado
- **AND** campo ausente permanece desconhecido e a observação bem-sucedida recebe instante UTC
- **AND** retries são limitados a uma repetição de GET idempotente; troca de código e revogação não são repetidas automaticamente

#### Scenario: Revogação da conexão

- **WHEN** o proprietário revoga a conexão com reautenticação válida
- **THEN** o backend solicita revogação ao Google, limpa o envelope de refresh token e registra estado revogado e instante
- **AND** resposta de erro preserva a conexão e não expõe corpo ou credencial do provedor
- **AND** em ambiente diferente de produção, a chamada real permanece bloqueada
