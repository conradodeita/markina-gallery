## Context

O produto possui um único fotógrafo administrador e múltiplos responsáveis/clientes. A experiência desejada é uma única porta de entrada, mas os fatores de autenticação e os destinos são diferentes. A tela não deve revelar se um telefone ou e-mail existe no sistema.

## Goals / Non-Goals

**Goals:**

- Uma rota visual única de login, responsiva e coerente com o frontend Markina Gallery.
- Fluxo de cliente por nome completo, telefone E.164 e OTP transacional via WhatsApp.
- Fluxo de administrador por e-mail, senha e TOTP.
- Sessão com papel emitido pelo backend e redirecionamento seguro.
- Cliente levado à galeria autorizada; múltiplas galerias levam à biblioteca.
- Auditoria, expiração, revogação e rate limit.

**Non-Goals:**

- Cadastro público de administrador.
- Login do administrador por WhatsApp como substituto de senha/TOTP.
- Autorização baseada em campos, URLs ou estado controlado apenas pelo browser.
- Implementação de WhatsApp/Evolution API real nesta etapa se o adaptador ainda estiver em sandbox.
- Sincronização desta spec para `openspec/specs/` antes da implementação validada.

## Decisions

### Decisão: uma tela, dois contextos de autenticação

A aplicação terá uma única rota de entrada, com escolha explícita de contexto (`Cliente` ou `Fotógrafo`) na própria tela. O contexto selecionado controla os campos exibidos, mas o backend valida novamente a identidade e o papel. Não haverá duas páginas de login visualmente independentes.

### Decisão: fluxo do cliente

O cliente informa nome completo e telefone. O servidor normaliza o telefone para E.164, cria um desafio OTP de uso único com expiração curta e envia o código pelo adaptador WhatsApp. Após validação, emite sessão com papel `client` e calcula as galerias autorizadas. Uma galeria única abre diretamente; várias galerias abrem a biblioteca do cliente.

### Decisão: fluxo do administrador

O fotógrafo informa e-mail e senha. Após a senha correta, o servidor exige TOTP compatível com Google Authenticator. Somente depois dos dois fatores válidos emite sessão com papel `admin` e redireciona para `/admin`.

### Decisão: roteamento seguro

O frontend pode solicitar o destino inicial, mas o servidor decide o destino final com base na sessão e nas autorizações. Rotas `/admin/*` exigem `admin`; rotas de cliente exigem `client` e relação válida com a galeria. Acesso negado não deve revelar se o recurso ou usuário existe.

### Decisão: sessão e auditoria

Sessões em cookies `HttpOnly`, `Secure` e `SameSite`, com expiração configurável, revogação e rotação. Registrar solicitação e validação de OTP, tentativas de senha/TOTP, sucesso, falha, logout e redirecionamento. Aplicar rate limit e invalidar desafios usados ou expirados.

## Contrato de implementação

Os endpoints abaixo permanecem internos ao mesmo domínio e não aceitam um destino informado pelo navegador. Respostas de autenticação usam mensagens neutras; detalhes de fator inválido, telefone inexistente ou vínculo ausente ficam somente na auditoria.

- `POST /auth/client/challenge`: recebe `full_name` e `phone`; normaliza para E.164, emite desafio opaco e retorna `202`.
- `POST /auth/client/verify`: recebe `challenge_id` e `code`; com sucesso cria sessão `client` e devolve somente o destino decidido no servidor.
- `POST /auth/admin/password`: recebe `email` e `password`; com credenciais válidas cria desafio administrativo curto, sem sessão.
- `POST /auth/admin/totp`: recebe `challenge_id` e `code`; somente um TOTP válido cria sessão `admin`.
- `GET /auth/destination` e `POST /auth/logout`: consultam exclusivamente o cookie de sessão.

Os valores aprovados são: OTP e desafio administrativo com 10 minutos de expiração, cinco tentativas por desafio, no máximo três reenvios e cinco solicitações por telefone/IP em 15 minutos. Senha e TOTP têm cinco tentativas por identidade/IP em 15 minutos. Sessões duram sete dias por padrão, são rotacionadas a cada autenticação e podem ser revogadas. O adaptador WhatsApp é sandbox nesta mudança: registra o envio sem expor o código em respostas HTTP.

## Registro de execução

- A aprovação de 1.1 foi recebida pela solicitação explícita do proprietário para aplicar esta mudança.
- Este contrato materializa as tarefas 1.2 e 1.3. Não inclui convite, recuperação de senha, códigos de recuperação, integração WhatsApp real nem gerenciamento de dispositivos, que pertencem a mudanças próprias.

## Risks / Trade-offs

- Uma tela com dois contextos adiciona uma pequena escolha inicial, mas evita inferência insegura de papel por e-mail/telefone.
- WhatsApp indisponível impede o OTP do cliente; a UI deve mostrar estado pendente e permitir reenvio limitado.
- O cliente pode estar vinculado a várias galerias; a biblioteca evita escolher uma galeria arbitrária.
