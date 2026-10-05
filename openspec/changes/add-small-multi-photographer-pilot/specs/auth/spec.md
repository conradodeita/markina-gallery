# Spec Delta

## ADDED Requirements

### Requirement: Recuperação uniforme de sessão e timeout

As superfícies protegidas de fotógrafo e cliente SHALL confirmar a sessão antes de montar conteúdo privado e ao retomar navegação/foco, periodicamente e após recusa de API. `/auth/destination` SHALL responder 401 para sessão ausente, expirada ou revogada e 403 para contexto não autorizado, sem dados pessoais ou enumeração; as demais rotas MUST preservar seu contrato existente. Perda confirmada SHALL desmontar conteúdo/cache facial privado e encaminhar à entrada com aviso e papel corretos. Destino de retorno MUST ser pathname interna permitida, sem query/token; retorno administrativo depende do destino confirmado pelo backend após senha/TOTP. Cliente sem link válido SHALL reabrir o link do fotógrafo para novo OTP, sem recuperar conta por UUID ou telefone. Falha de rede/408/5xx ou timeout da leitura SHALL permitir tentativa explícita sem logout, looping ou replay de mutação/OTP. Autorização 403 com sessão válida SHALL permanecer acesso negado, não expiração.

#### Scenario: Sessão expirada na área do fotógrafo
- **WHEN** a verificação confirma sessão expirada enquanto uma rota administrativa está aberta
- **THEN** o conteúdo privado é desmontado e a entrada Fotógrafo informa a necessidade de senha e TOTP novamente

#### Scenario: Sessão cliente expirada sem capacidade de convite
- **WHEN** a sessão da galeria expira e não existe link válido apresentado
- **THEN** a entrada Cliente orienta reabrir o link original, sem conceder acesso pelo UUID da galeria

#### Scenario: Falha temporária não é logout
- **WHEN** a rede falha ou a API responde 408/5xx na superfície protegida
- **THEN** há aviso claro e retry da leitura de sessão, sem repetir uploads, pedidos ou envio de OTP e sem invalidar sessão válida

#### Scenario: Permissão específica recusada
- **WHEN** uma API responde 403 mas a sessão contextual continua válida
- **THEN** a interface indica acesso negado sem redirecionar automaticamente para login

#### Scenario: Entrada pública e URL externa
- **WHEN** a página pública de login/recuperação está aberta ou uma requisição não pertence à API da mesma origem
- **THEN** a fronteira protegida não intercepta esse fluxo nem transforma erro de credencial em loop de redirecionamento

## MODIFIED Requirements

### Requirement: Contexto administrativo vinculado à conta do fotógrafo

O backend SHALL resolver o contexto do fotógrafo pela sessão administrativa persistida e seu único vínculo ativo inequívoco com uma conta ativa, revalidando conta e vínculo nas operações protegidas e antes do commit. O sistema MUST preservar os fatores de autenticação existentes e não usar identificadores enviados pelo frontend como autoridade para escolher a conta. Ausência, revogação ou ambiguidade de vínculo SHALL recusar a operação sem fallback; a presença de outra conta válida na instalação SHALL preservar o acesso independente autorizado.

#### Scenario: Administrador legado vinculado
- **WHEN** o administrador atual, migrado com vínculo ativo, conclui senha e TOTP
- **THEN** sua sessão permite operação somente na conta vinculada sem exigir novo cadastro

#### Scenario: Vínculo revogado após login
- **WHEN** o vínculo administrativo é desativado enquanto a sessão ainda é válida
- **THEN** a próxima operação protegida é recusada sem expor recursos ou reutilizar contexto anterior

#### Scenario: Tentativa de impor proprietário
- **WHEN** uma requisição administrativa inclui outro identificador de conta na URL, corpo ou cabeçalho
- **THEN** esse identificador não substitui o contexto autorizado e não permite leitura, alteração ou criação para outra conta

#### Scenario: Sessão sem vínculo
- **WHEN** uma sessão administrativa válida não possui vínculo ativo inequívoco com uma conta ativa
- **THEN** a operação protegida é recusada sem fallback para a primeira conta encontrada

#### Scenario: Contas independentes
- **WHEN** a instalação contém A e B ativas com administradores vinculados separadamente
- **THEN** cada administrador opera sua própria conta, e suspensão ou revogação em A não concede acesso a B nem bloqueia o administrador válido de B

### Requirement: OTP de cliente por WhatsApp

O sistema SHALL autenticar cliente/responsável mediante nome completo, telefone normalizado em E.164 e OTP de uso único enviado pelo adaptador WhatsApp vinculado à conta do fotógrafo. O contexto SHALL ser derivado no backend de link válido de galeria/convite ou sessão contextual válida. Desafios, reenvios, verificação e sessão resultante SHALL permanecer associados à mesma conta; um telefone não seleciona conta global. Entrada sem contexto em instalação com várias contas SHALL solicitar o link do fotógrafo, sem enumerar contas ou clientes. Rate limit SHALL incluir proteção global contra abuso e separação contextual.

#### Scenario: Cliente solicita código
- **WHEN** a cliente informa dados válidos em contexto autorizado e solicita entrada
- **THEN** o sistema cria desafio OTP contextual com expiração curta, envia o código pelo canal vinculado e exibe a validação sem revelar se o telefone está cadastrado

#### Scenario: Cliente valida código
- **WHEN** a cliente informa o OTP correto no mesmo contexto dentro do prazo
- **THEN** o sistema invalida o desafio, cria sessão com papel `client` restrita à conta e encaminha conforme suas galerias autorizadas nessa conta

#### Scenario: OTP inválido, usado ou expirado
- **WHEN** a cliente informa código inválido, já usado ou expirado
- **THEN** o sistema rejeita a autenticação, registra a tentativa sem segredo, mantém resposta neutra e aplica rate limit

#### Scenario: OTP de outro fotógrafo
- **WHEN** um desafio emitido para A é apresentado no fluxo de B, mesmo com telefone igual
- **THEN** a autenticação é recusada sem vincular ou criar sessão de B

#### Scenario: Entrada sem contexto
- **WHEN** uma visitante sem sessão contextual abre a entrada cliente sem link em instalação com várias contas
- **THEN** a interface orienta usar o link enviado pelo fotógrafo sem pesquisar telefone em todas as contas

### Requirement: Roteamento por papel e autorização

O backend SHALL determinar o destino e autorizar cada rota usando papel, conta ativa e relações persistidas da sessão. O fotógrafo SHALL operar somente a conta vinculada; vínculos ausentes, revogados ou ambíguos SHALL negar acesso sem fallback. A sessão cliente SHALL identificar cadastro e conta específicos; outra conta SHALL exigir sua própria autenticação. URLs, cookies não autorizados ou estado frontend MUST NOT conceder acesso. Revogação em uma conta SHALL preservar sessões independentes de outra.

#### Scenario: Administrador acessa rota administrativa
- **WHEN** uma sessão `admin` com vínculo ativo inequívoco acessa `/admin`
- **THEN** o sistema permite entrada somente na área administrativa da conta vinculada

#### Scenario: Cliente acessa galeria única
- **WHEN** uma sessão `client` possui uma única galeria autorizada na sua conta
- **THEN** o sistema redireciona diretamente para essa galeria

#### Scenario: Cliente possui várias galerias
- **WHEN** uma sessão `client` possui duas ou mais galerias autorizadas na sua conta
- **THEN** o sistema redireciona para a biblioteca dessa conta sem incluir galerias de outras

#### Scenario: Papel incompatível
- **WHEN** uma sessão `client` tenta acessar `/admin`, ou qualquer sessão tenta recurso de outra conta sem autorização própria
- **THEN** o sistema nega acesso sem revelar existência do recurso e registra evento sanitizado

#### Scenario: Vínculo administrativo revogado
- **WHEN** o vínculo da sessão administrativa é revogado ou a conta é suspensa
- **THEN** a próxima operação da conta é recusada sem reutilizar contexto ou cache autorizado anteriormente
