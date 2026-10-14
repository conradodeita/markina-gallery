## MODIFIED Requirements

### Requirement: OTP de cliente por WhatsApp
O sistema SHALL autenticar cliente mediante nome completo, telefone normalizado em E.164 e OTP de uso único enviado pelo adaptador WhatsApp. Uma sessão existente SHALL poder retomar vínculos já autorizados, mas a criação de vínculo com uma nova Galeria pública ou privada SHALL exigir novo OTP contextual, sem criar outra identidade para o mesmo telefone.

#### Scenario: Cliente solicita código
- **WHEN** o cliente informa dados válidos e solicita entrada
- **THEN** o sistema cria desafio OTP com expiração curta, envia o código pelo WhatsApp e exibe a etapa de validação sem revelar se o telefone está cadastrado

#### Scenario: Cliente valida código
- **WHEN** o cliente informa o OTP correto dentro do prazo
- **THEN** o sistema invalida o desafio, cria ou renova sessão com papel `client` e encaminha o cliente conforme suas galerias autorizadas

#### Scenario: Telefone já cadastrado pelo fotógrafo
- **WHEN** uma cliente informa o mesmo telefone E.164 de um cadastro administrativo e valida o OTP
- **THEN** o sistema reutiliza o mesmo `Client.id`, materializa a verificação nesse cadastro e SHALL NOT criar outra identidade nem sobrescrever silenciosamente seu nome

#### Scenario: Nova origem com sessão existente
- **WHEN** uma cliente autenticada abre link de Galeria pública ou privada à qual ainda não está vinculada
- **THEN** o backend exige OTP contextual, reutiliza a identidade canônica após validação e cria somente os vínculos permitidos pelo link

#### Scenario: OTP inválido, usado ou expirado
- **WHEN** o cliente informa código inválido, já usado ou expirado
- **THEN** o sistema rejeita a autenticação, registra a tentativa, mantém resposta neutra e aplica rate limit

### Requirement: Roteamento por papel e autorização
O backend SHALL determinar destino e autorizar cada rota usando papel, telefone verificado, vínculo com a Galeria pública e associação com a galeria privada, nunca somente frontend, URL ou estado local. Dentro da mesma Galeria pública, cada cliente SHALL estar associada a no máximo uma privada operacional.

#### Scenario: Administrador acessa rota administrativa
- **WHEN** uma sessão `admin` acessa `/admin`
- **THEN** o sistema permite a entrada na área administrativa

#### Scenario: Cliente acessa galeria única
- **WHEN** uma sessão `client` possui uma única origem autorizada
- **THEN** o sistema redireciona para a Galeria pública enquanto disponível ou para a privada autorizada de contingência quando a origem não puder ser aberta

#### Scenario: Cliente possui várias origens
- **WHEN** uma sessão `client` possui galerias autorizadas de duas ou mais Galerias públicas
- **THEN** o sistema redireciona para a biblioteca, apresentando uma única jornada por origem com sua privada operacional correspondente embutida

#### Scenario: Cliente possui várias galerias
- **WHEN** uma sessão `client` possui duas ou mais galerias autorizadas
- **THEN** o sistema redireciona para a biblioteca e mostra somente jornadas e históricos autorizados àquela identidade, sem duplicar a privada automática como outro card

#### Scenario: Link privado conflita com vínculo existente
- **WHEN** o telefone já pertence a uma privada da mesma Galeria pública e conclui OTP por outro link privado dessa origem
- **THEN** o sistema não cria segundo vínculo e encaminha de forma segura para a privada já autorizada

#### Scenario: Membro bloqueado tenta novo link
- **WHEN** uma cliente bloqueada tenta contornar o bloqueio com outro link privado da mesma origem
- **THEN** o backend mantém o bloqueio, não cria nova associação e responde sem revelar membros ou privadas de terceiros

#### Scenario: Papel incompatível
- **WHEN** uma sessão `client` tenta acessar `/admin` ou galeria sem autorização
- **THEN** o sistema responde com acesso negado sem revelar a existência do recurso e registra o evento
