## ADDED Requirements

### Requirement: Recuperação administrativa com fatores encadeados

O sistema SHALL oferecer `Esqueci minha senha` somente no contexto `Fotógrafo` e SHALL exigir, nesta ordem, um desafio de recuperação iniciado pelo e-mail, um OTP enviado ao WhatsApp administrativo verificado e um link enviado ao e-mail cadastrado. Nenhuma etapa isolada SHALL criar sessão administrativa, revelar a existência da conta ou substituir o login normal por senha e TOTP.

#### Scenario: Solicitação para conta elegível

- **WHEN** uma pessoa solicita recuperação com o e-mail verificado da conta administrativa e os canais de recuperação estão aptos
- **THEN** o sistema aplica rate limit, cria um desafio curto e envia um OTP de uso único ao WhatsApp administrativo verificado, retornando a mesma resposta pública usada para e-mails desconhecidos

#### Scenario: Solicitação para e-mail desconhecido ou conta inelegível

- **WHEN** uma pessoa solicita recuperação com e-mail desconhecido, não verificado ou sem canal de recuperação apto
- **THEN** o sistema mantém resposta, tempo e formato públicos neutros, não envia mensagem e registra somente evidência sanitizada para segurança

#### Scenario: OTP de recuperação válido

- **WHEN** o OTP correto é informado dentro do prazo e dos limites de tentativa para um desafio elegível
- **THEN** o sistema consome o desafio, invalida solicitações de recuperação anteriores e enfileira um único link para o e-mail cadastrado

#### Scenario: OTP inválido, usado ou expirado

- **WHEN** o OTP de recuperação é inválido, já usado, expirou ou excedeu tentativas
- **THEN** o sistema rejeita a continuação com resposta neutra, não enfileira e-mail e registra a tentativa sem OTP, e-mail ou telefone em claro

### Requirement: Redefinição por link único e de curta duração

O sistema SHALL aceitar redefinição de senha somente mediante token opaco de alta entropia, armazenado exclusivamente como hash, vinculado à finalidade e à conta, com expiração curta e uso único. Uma redefinição bem-sucedida SHALL revogar todas as sessões administrativas e tokens de recuperação pendentes e SHALL exigir novo login completo com senha e TOTP.

#### Scenario: Link válido redefine a senha

- **WHEN** o administrador apresenta token válido e uma nova senha compatível com a política forte
- **THEN** o sistema grava somente o hash Argon2id da nova senha, consome todos os tokens de recuperação da conta, revoga as sessões administrativas e confirma a redefinição sem autenticar automaticamente

#### Scenario: Link inválido, expirado ou reutilizado

- **WHEN** o token não existe, expirou, já foi usado ou foi invalidado por solicitação posterior
- **THEN** o sistema não altera credenciais, retorna resposta segura sem detalhes enumeráveis e registra a falha com identificador irreversível

#### Scenario: Nova senha não atende à política

- **WHEN** a nova senha é curta, comum, coincide com a senha atual ou excede os limites de entrada aceitos
- **THEN** o sistema rejeita a redefinição sem consumir um token ainda válido e informa somente os critérios de senha aplicáveis

#### Scenario: Concorrência no consumo do link

- **WHEN** duas requisições tentam usar simultaneamente o mesmo token válido
- **THEN** exatamente uma alteração é confirmada e todas as demais são rejeitadas como token indisponível

### Requirement: Segurança da conta em Configurações

O sistema SHALL permitir que o administrador autenticado consulte seu e-mail mascarado e solicite troca de senha ou de e-mail em `Configurações`. As duas alterações SHALL exigir reautenticação pela senha atual e OTP no WhatsApp administrativo verificado, SHALL aplicar rate limit e SHALL produzir auditoria sem dados sensíveis.

#### Scenario: Troca autenticada de senha

- **WHEN** uma sessão administrativa válida apresenta a senha atual, conclui o OTP da ação sensível e fornece nova senha compatível
- **THEN** o sistema troca o hash da senha, revoga todas as sessões administrativas e desafios relacionados e exige novo login completo

#### Scenario: Tentativa de troca de senha sem confirmação

- **WHEN** a senha atual ou o OTP da ação sensível é inválido, usado, expirado ou pertence a outra finalidade
- **THEN** o sistema não altera a senha, não aceita reutilização cruzada do desafio e registra a falha de forma sanitizada

#### Scenario: Solicitação de troca de e-mail

- **WHEN** uma sessão administrativa válida apresenta a senha atual, conclui o OTP da ação sensível e informa um novo e-mail válido e ainda disponível
- **THEN** o sistema mantém o e-mail atual como identidade ativa, invalida pedidos anteriores de troca e envia ao novo endereço um link de verificação de uso único

#### Scenario: Confirmação do novo e-mail

- **WHEN** o link de verificação do novo endereço é consumido dentro do prazo
- **THEN** o sistema promove atomicamente o novo e-mail verificado, revoga sessões e tokens administrativos pendentes, exige novo login e envia aviso sanitizado ao endereço anterior

#### Scenario: Link de troca inválido ou vencido

- **WHEN** o link de verificação não é válido, expirou, já foi usado ou foi substituído por pedido posterior
- **THEN** o e-mail atual permanece inalterado e o sistema não revela dados da conta nem do endereço pretendido

#### Scenario: Novo e-mail já utilizado

- **WHEN** o endereço pretendido já pertence a outra identidade administrativa ou conflita no momento da confirmação
- **THEN** o sistema não altera a identidade ativa, invalida com segurança o pedido conflitante e apresenta orientação sem expor a outra conta

### Requirement: Auditoria e minimização da recuperação administrativa

O sistema SHALL auditar solicitação, bloqueio, validação de OTP, emissão e consumo de link, alteração de senha, alteração de e-mail e revogação de sessões. Eventos e registros transitórios MUST excluir senha, OTP, token bruto, corpo de e-mail e dados de contato em claro quando não forem estritamente necessários à entrega em andamento.

#### Scenario: Consulta administrativa da auditoria

- **WHEN** eventos de recuperação ou alteração de credencial são registrados
- **THEN** a evidência contém finalidade, resultado, horários, identificadores irreversíveis e correlação suficiente para investigação, sem revelar os segredos utilizados

#### Scenario: Fluxo alcança estado terminal

- **WHEN** um desafio, token ou entrega sensível é consumido, invalidado, expirado ou encerrado
- **THEN** o sistema elimina o material recuperável conforme a janela operacional documentada e preserva somente hashes e metadados mínimos de auditoria e antifraude
