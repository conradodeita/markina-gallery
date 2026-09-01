## Context

Consulte `proposal.md` para a motivação e os delta specs para o comportamento exigido. A autenticação atual possui `AdminUser` com e-mail verificado, hash Argon2id e TOTP, desafios genéricos, sessões revogáveis, rate limit baseado em auditoria e OTP de cliente entregue pela outbox WhatsApp. Não há token de recuperação, transporte de e-mail, alteração de credenciais em Configurações nem um telefone separado na conta administrativa; o canal WhatsApp já mantém número esperado, número conectado e estado `ready` verificado em fail closed.

O mandato exige recuperação por e-mail, confirmação WhatsApp para recuperação/troca de senha, SMTP transacional e auditoria. Segredos do provedor e chaves de cifra continuam exclusivos do ambiente; a ativação externa não faz parte da implementação local automática.

## Goals / Non-Goals

**Goals:**

- Encadear duas provas de posse na recuperação: WhatsApp administrativo verificado e e-mail cadastrado, sem emitir sessão.
- Tornar tokens, desafios e alterações concorrentes de uso único e atomicamente consumíveis.
- Introduzir transporte de e-mail durável, testável em sandbox e substituível por SMTP real.
- Disponibilizar troca de senha e e-mail em Configurações com reautenticação, confirmação sensível e revogação de sessões.
- Evitar enumeração de conta e vazamento de destinatários, OTPs, tokens, senhas ou links em banco consultável, API e logs.

**Non-Goals:**

- Recuperar ou desativar TOTP, implementar códigos de recuperação ou substituir o login administrativo por WhatsApp.
- Criar múltiplos administradores, cadastro público, edição do telefone de recuperação ou inbox de e-mail/WhatsApp.
- Escolher ou contratar um fornecedor SMTP específico, alterar DNS ou ativar efeitos externos durante a implementação local.
- Reestruturar a outbox WhatsApp existente ou tratar e-mail como confirmação de entrega ao destinatário final.

## Decisions

### 1. O canal WhatsApp pronto define o telefone administrativo verificado

Enquanto o MVP possui um único fotógrafo, o destinatário do OTP sensível será o número do canal WhatsApp cujo estado é `ready` e cuja identidade conectada coincide com o número esperado segundo a canonização brasileira já especificada. Recuperação e alteração de credencial falham em modo fechado quando o canal está ausente, divergente ou indisponível. O e-mail nunca é usado para escolher o telefone e nenhum número vindo do navegador participa da entrega.

Essa decisão reutiliza a prova operacional de pareamento existente e evita criar um segundo cadastro telefônico sem fluxo de verificação. Alternativa descartada: aceitar telefone digitado durante a recuperação, pois permitiria desviar o OTP e enumerar a conta. Uma futura troca independente de telefone administrativo exigirá change própria e confirmação do número anterior ou procedimento de recuperação assistida.

### 2. Desafios administrativos ficam isolados dos desafios de cliente

Uma tabela aditiva `admin_security_challenge` representará `password_recovery_otp`, `change_password_otp` e `change_email_otp`. Ela terá `admin_id` anulável para produzir um fluxo sintético indistinguível quando o e-mail inicial não for elegível, impressão irreversível do sujeito/alvo, hash do OTP, finalidade, expiração, tentativas, consumo e correlação com sessão quando aplicável. O alvo de troca de e-mail será cifrado e seu hash será vinculado ao desafio.

Separar o modelo reduz o risco de quebrar a lógica já implantada de OTP de cliente e impede reutilização cruzada por `kind`. Alternativa considerada: ampliar `AuthChallenge`; rejeitada porque seus campos de galeria e regras de minimização pertencem ao acesso de cliente e produziriam invariantes difíceis de verificar.

Solicitações públicas sempre retornam `202` com um identificador opaco de desafio. Para e-mail inexistente/inelegível, o desafio sintético recebe segredo aleatório não entregue e passa pelas mesmas validações e limites. Auditoria e rate limit usam HMAC com segredo do servidor, nunca e-mail em claro.

### 3. O fluxo público usa WhatsApp antes do link de e-mail

O contrato será:

1. `POST /auth/admin/recovery/challenge` recebe e-mail, normaliza, limita por impressão/IP e cria desafio real ou sintético; quando elegível, enfileira OTP WhatsApp para o canal administrativo pronto.
2. `POST /auth/admin/recovery/verify` recebe desafio e OTP. O consumo válido invalida desafios/tokens anteriores da mesma finalidade, gera token aleatório de 256 bits, persiste somente seu SHA-256 e enfileira o link para o e-mail cadastrado.
3. `POST /auth/admin/recovery/reset` recebe token e nova senha, consome atomicamente o token e, após validação, troca o hash, revoga todas as sessões/desafios/tokens e exige login normal.

O OTP terá padrão de 10 minutos, cinco tentativas e no máximo três reenvios dentro dos limites já adotados. O token de redefinição terá padrão de 15 minutos e somente o token mais recente permanecerá válido. Tempos poderão ser reduzidos por configuração segura, nunca ampliados pelo navegador.

Alternativas descartadas: enviar o link imediatamente após informar o e-mail, que não cumpre a recuperação controlada por WhatsApp; ou permitir que OTP sozinho redefina a senha, que elimina a prova do e-mail cadastrado.

### 4. Links usam fragmento e consumo explícito por POST

O e-mail conterá URL HTTPS construída a partir de uma origem pública fixa permitida pelo servidor, como `/admin/reset-password#token=<opaco>` ou `/admin/verify-email#token=<opaco>`. Fragmentos não são enviados no request inicial nem em `Referer`; a página lê o token, remove-o imediatamente da barra/histórico com `history.replaceState` e o envia somente no corpo do POST de consumo. Respostas usarão `Referrer-Policy: no-referrer` e as páginas não carregarão recursos de terceiros.

Scanners de link não consumirão o token por GET. Alternativas descartadas: token em query/path, que tende a aparecer em logs, histórico e métricas, e consumo por GET, que pode ser acionado por pré-visualizadores.

### 5. Tokens de ação são hash-only e consumidos atomicamente

`admin_action_token` armazenará `token_hash`, `purpose`, `admin_id`, expiração, consumo e, para troca de e-mail, o alvo cifrado e sua impressão. Um índice único no hash e atualização condicional dentro da transação garantem que apenas uma requisição concorrente consuma o token. Nova emissão invalida tokens anteriores da mesma finalidade; redefinição de senha ou promoção de e-mail invalida todos os tokens e desafios da conta.

O token bruto só existirá na memória da requisição e no payload autenticadamente cifrado da outbox. Alternativa descartada: persistir token bruto para facilitar reenvio, pois uma leitura do banco concederia acesso à conta.

### 6. Política de senha central e revogação conservadora

Um único validador será usado por seed, redefinição e Configurações: entre 12 e 128 caracteres, sem coincidência com o e-mail normalizado, rejeição de valores comuns mantidos pelo projeto e rejeição da senha atual. O hash continuará Argon2id; entradas acima do limite serão rejeitadas antes do cálculo para reduzir abuso de recursos.

Toda troca bem-sucedida revoga inclusive a sessão atual, remove o cookie quando houver e exige senha + TOTP novamente. Essa escolha é mais segura e previsível do que tentar preservar a sessão originadora. Histórico de hashes não será mantido nesta change; portanto, além da senha imediatamente atual, reutilização antiga não poderá ser detectada.

### 7. Configurações usa desafio vinculado à sessão, finalidade e alvo

Endpoints autenticados de segurança exigirão sessão `admin`, origem same-site e senha atual antes de criar o desafio WhatsApp. O desafio registra a sessão e a finalidade; na troca de e-mail também vincula a impressão do novo endereço. A conclusão recebe desafio, OTP e o novo valor, revalida sessão/finalidade/alvo e executa a alteração em uma transação.

Na troca de e-mail, o endereço atual permanece ativo. Após OTP, o sistema cria token `verify_admin_email` e envia ao novo endereço. O consumo promove o endereço somente se ainda estiver disponível, revoga sessões/tokens e enfileira aviso ao endereço anterior. Pedidos posteriores invalidam os anteriores.

Alternativas descartadas: alterar e-mail antes de verificar o novo destino, o que poderia bloquear a conta por erro de digitação; e confiar apenas na sessão, o que amplia o impacto de sessão roubada.

### 8. E-mail terá outbox própria e provider pequeno

Uma tabela `email_delivery` e tentativas relacionadas armazenará finalidade, origem, impressão do destinatário, idempotência, payload cifrado, validade, estado, tentativas, identificador externo opcional e erro sanitizado. O endereço, assunto, texto e link ficarão no envelope cifrado com AEAD e chave exclusiva `EMAIL_PAYLOAD_ENCRYPTION_KEY`; após aceitação, expiração ou falha terminal, o payload será apagado.

Uma interface `EmailProvider.send()` terá adaptadores `sandbox` e `smtp`. O sandbox não abre rede nem registra conteúdo; testes injetam um fake controlado para inspecionar a mensagem. SMTP usará TLS obrigatório, timeout curto e configuração exclusiva de ambiente. O worker já existente processará entregas em lotes com claim atômico, validade e backoff. Timeout depois de possível aceitação irá para estado de reconciliação/erro ambíguo sem reenvio cego do mesmo link.

Uma outbox separada evita modificar constraints e estados da entrega WhatsApp enquanto sua change ainda aguarda validações humanas. Alternativa considerada: generalizar imediatamente ambas em `message_delivery`; rejeitada por ampliar migração, rollback e superfície de regressão sem benefício necessário para esta entrega.

### 9. O frontend mantém recuperação fora da sessão e segurança dentro de Configurações

A entrada do fotógrafo exibirá `Esqueci minha senha` sem alterar o contexto Cliente. O fluxo terá solicitação, OTP, confirmação de e-mail enfileirado, redefinição e retorno ao login, sempre com mensagens neutras. `Configurações` ganhará seção `Segurança da conta`, com e-mail atual mascarado, formulários separados para senha e e-mail, estados de desafio e aviso explícito de que a sessão será encerrada.

As telas não persistirão tokens em storage, não renderizarão contato completo vindo de endpoint público e terão estados acessíveis de carregamento, erro, expiração e sucesso. O backend continuará sendo a autoridade; esconder controles no frontend não substitui autorização.

## Risks / Trade-offs

- [O número conectado envia mensagem para ele próprio e o provedor pode não suportar self-message] → validar com fake e sandbox local; antes de declarar SMTP/recuperação reais prontos, executar teste sintético no canal homologado e manter fail closed se o provider rejeitar.
- [Resposta pública sintética ainda pode vazar existência por tempo ou volume] → realizar trabalho persistente equivalente, usar mensagens/formato iguais, HMAC de identidade e testes de enumeração; não prometer resistência absoluta a análise lateral da infraestrutura.
- [SMTP aceita a mensagem, mas ela cai em spam ou atrasa] → SPF/DKIM/DMARC, remetente próprio do ambiente, validade curta, botão de nova solicitação limitado e painel de pendência; `accepted` não será apresentado como leitura.
- [Payload cifrado depende de chave operacional] → falhar fechado fora de desenvolvimento, documentar rotação/backup da chave e nunca reutilizar credencial SMTP como chave de cifra.
- [Revogar todas as sessões causa atrito] → comunicar antes da ação e privilegiar segurança para o único administrador do MVP.
- [Troca de e-mail concorre com novo pedido ou endereço já usado] → token mais recente vence e a promoção usa transação/constraint única, mantendo o e-mail anterior em qualquer conflito.
- [A outbox separada duplica parte da infraestrutura de mensageria] → manter contrato mínimo e avaliar unificação somente em change futura após estabilização das duas integrações.

## Migration Plan

1. Criar migration exclusivamente aditiva para desafios administrativos, tokens de ação, entregas de e-mail e tentativas, sem alterar credenciais ou sessões existentes.
2. Implementar domínio, providers sandbox/fake, worker e testes de segurança; manter `EMAIL_PROVIDER=sandbox` como padrão e não exigir segredos reais para CI/desenvolvimento.
3. Implementar endpoints e frontend, habilitando a interface somente quando o backend reportar canais necessários; ausência de SMTP/WhatsApp real gera estado operacional claro, não bypass.
4. Documentar variáveis sem valores, origem HTTPS, healthcheck, SPF/DKIM/DMARC, rollback e inventário. Validar migration do zero e sobre o head vigente.
5. Para homologação, apresentar inventário de impacto zero e obter autorização explícita. Aplicar migration antes do código, manter sandbox até os segredos próprios do ambiente estarem configurados e então executar recuperação sintética completa.
6. Em rollback, desabilitar o provider real e retornar à versão anterior sem apagar tabelas; tokens novos deixam de ser consumíveis pela aplicação antiga, sessões já revogadas não são restauradas e a migration downgrade só poderá ocorrer após inventário de dados.

## Open Questions

- O fornecedor SMTP transacional e o remetente definitivo serão escolhidos na preparação operacional de homologação. O contrato genérico, o sandbox e os testes locais não dependem dessa escolha.
