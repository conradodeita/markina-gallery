# Operação de recuperação e segurança da conta administrativa

Este runbook cobre somente a Markina Gallery. Ele não autoriza alteração de credenciais, DNS, proxy, firewall, containers ou volumes de terceiros.

## Fluxos e contratos

### Recuperação pública

1. `POST /auth/admin/recovery/challenge` recebe `{ "email": string }` e sempre responde de forma neutra com `202`, um `challenge_id` e mensagem não enumerável.
2. O OTP de seis dígitos é enviado apenas ao WhatsApp administrativo configurado e pronto. O desafio expira em 10 minutos, aceita no máximo 5 tentativas e 3 reenvios por `POST /auth/admin/recovery/resend`.
3. `POST /auth/admin/recovery/verify` recebe `challenge_id` e `code`. Se elegível, enfileira no e-mail cadastrado um link de uso único com validade de 15 minutos.
4. A página `/admin/reset-password` retira o token do fragmento `#token=...` imediatamente, não usa `localStorage`/`sessionStorage` e envia `{ "token", "new_password" }` somente em `POST /auth/admin/recovery/reset`.
5. O sucesso revoga todas as sessões e exige novo login com senha e TOTP; nunca cria sessão automaticamente.

### Configurações autenticadas

- `GET /admin/security/summary` retorna somente e-mail mascarado e estados sanitizados de WhatsApp/e-mail.
- `POST /admin/security/password/challenge` exige senha atual e sessão administrativa; `POST /admin/security/password/confirm` exige o OTP da mesma sessão e a nova senha.
- `POST /admin/security/email/challenge` exige senha atual, novo e-mail e sessão administrativa; `POST /admin/security/email/verify-otp` envia o link ao novo endereço.
- `/admin/verify-email#token=...` só efetiva a troca em `POST /auth/admin/email/confirm`. O endereço anterior permanece ativo em qualquer falha e recebe aviso depois do sucesso.
- As mutações autenticadas validam `Origin`; senha ou e-mail alterado revoga todas as sessões.

## Política de senha

A senha administrativa MUST ter entre 12 e 128 caracteres, não pode ser comum, conter a parte local do e-mail nem reutilizar a senha atual. O armazenamento usa Argon2id. Senha, OTP e token nunca são registrados em claro.

## Configuração externa

Os nomes abaixo devem existir somente no arquivo externo do ambiente ou no gerenciador de secrets. `.env.example` não contém valores reais.

| Variável | Uso |
| --- | --- |
| `EMAIL_PROVIDER` | `sandbox` sem efeito externo ou `smtp` para entrega real |
| `EMAIL_CREDENTIAL_ENV` | Deve ser exatamente igual a `APP_ENV` |
| `EMAIL_PAYLOAD_ENCRYPTION_KEY` | Chave AES-GCM urlsafe-base64 de 32 bytes, exclusiva do ambiente |
| `PUBLIC_APP_ORIGIN` | Origem canônica HTTPS, sem caminho, credencial, query ou fragmento |
| `SMTP_HOST`, `SMTP_PORT` | Endpoint SMTP próprio do ambiente |
| `SMTP_USER`, `SMTP_PASSWORD` | Credenciais externas; nunca registrar ou versionar |
| `SMTP_FROM_ADDRESS` | Remetente verificado no provedor |
| `SMTP_TIMEOUT_SECONDS` | Timeout entre 1 e 30 segundos |
| `SMTP_IMPLICIT_TLS` | `true` para TLS implícito; caso contrário usa STARTTLS obrigatório |
| `EMAIL_MAX_ATTEMPTS` | 1 a 10; padrão 3 |
| `EMAIL_RETRY_BASE_SECONDS` | Base exponencial, limitada a 300 segundos |
| `EMAIL_PROCESSING_TIMEOUT_SECONDS` | Processamento abandonado vira `unknown`; padrão 120 segundos |
| `ADMIN_SECURITY_CLEANUP_INTERVAL_SECONDS` | Intervalo do worker de minimização; mínimo 5 segundos |

O modo `sandbox` não abre conexão de rede nem guarda conteúdo em log. Em homologação, ausência ou divergência de chave, origem, credencial ou ambiente MUST falhar fechada; a interface exibirá o canal como indisponível/sandbox.

## DNS e reputação do remetente

Antes de habilitar SMTP real em homologação, o operador humano deve:

1. validar o domínio/remetente no provedor;
2. publicar SPF autorizando somente os emissores necessários;
3. habilitar DKIM e confirmar a assinatura recebida;
4. publicar DMARC inicialmente com política e relatórios apropriados ao domínio, endurecendo a política após observação;
5. testar com caixas sintéticas e conferir `SPF=pass`, `DKIM=pass` e `DMARC=pass` nos cabeçalhos recebidos.

Não use dados reais de clientes nos testes. DNS e credenciais exigem ação humana e não são modificados pelo deploy da aplicação.

## Outbox, retenção e reconciliação

- Destinatário, assunto e corpo ficam cifrados enquanto a entrega está pendente.
- Estados terminais `accepted`, `failed`, `unknown` e `expired` removem o payload recuperável; permanecem somente IDs, timestamps, estado, tentativas e erro sanitizado para auditoria.
- Timeout após aceitação possível vira `unknown` e MUST NOT ser reenviado cegamente. O operador deve reconciliar no provedor antes de qualquer nova ação.
- Tokens persistem somente por SHA-256; alvos temporários ficam cifrados e são apagados quando usados, invalidados ou expirados.

## Diagnóstico

1. Consulte Configurações > Segurança da conta ou `GET /admin/email/channel` com sessão administrativa. A resposta não expõe host, usuário, senha, destinatário ou link.
2. Se `sandbox`, confirme `EMAIL_PROVIDER` no ambiente externo.
3. Se indisponível, confira presença (não o valor em logs) de `EMAIL_PAYLOAD_ENCRYPTION_KEY`, `PUBLIC_APP_ORIGIN` e variáveis SMTP, além da igualdade `EMAIL_CREDENTIAL_ENV=APP_ENV`.
4. Confirme acesso de saída ao SMTP e relógio UTC. Não imprima payloads cifrados/decriptados.
5. Para estado `unknown`, reconcilie pelo ID externo sanitizado e horário antes de repetir a solicitação pelo produto.

## Deploy e rollback

O deploy executa a migration aditiva `20260831_0032_admin_account_recovery`, sem remover nem alterar credenciais existentes. Antes de publicar: backup vigente, `alembic current`, inventário de containers/volumes/porta/subdomínio e validações completas.

Rollback de aplicação: retorne ao SHA saudável anterior usando somente `-p markina-gallery -f docker/docker-compose.yml`. A migration pode permanecer aplicada por ser aditiva e compatível; não execute downgrade em homologação sem nova autorização explícita. Se SMTP causar impacto, altere externamente `EMAIL_PROVIDER=sandbox` e recrie apenas `api` e `worker` da Markina Gallery após aprovação operacional.
