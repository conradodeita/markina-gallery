# Spec Delta

## MODIFIED Requirements

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
