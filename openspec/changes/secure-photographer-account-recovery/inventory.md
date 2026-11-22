# Inventário de recuperação — 10/11/2026

Leitura estática local, sem consultar dados pessoais, configuração operacional ou serviços externos.

| Caminho | Prova e efeitos atuais | Reaproveitamento / limite |
| --- | --- | --- |
| `photographer_signup.request_email_recovery` | Signup ativo, e-mail verificado e vínculo; resposta pública neutra; link cifrado no outbox | Primeiro caminho de fotógrafo SaaS com e-mail disponível. |
| `main.admin_password_reset` | Token password_reset; senha validada; exige TOTP/código de recuperação quando fator ativado; consumo único | Preservar no fluxo comum; não transformar novo e-mail em prova da conta antiga. |
| `main.admin_recovery_challenge`, `admin_account.create_security_challenge` | Caminho legado por OTP WhatsApp usando canal do tenant | Não anunciar como telefone pessoal verificado de fotógrafo SaaS. `AdminUser` não tem atributo de telefone pessoal verificado. |
| `main.issue_admin_totp_recovery_codes`, `totp_recovery.py` | Códigos com hash, seletor, consumo/revogação; TOTP não reutiliza passo | Reutilizar verificação e invalidação; preservar regras comuns. |
| `photographer_totp_support` | Elegibilidade SaaS, exclusão de PlatformOwner, senha/TOTP do proprietário, versão e rechecagem da sessão | Reutilizar autorização e componentes de atendimento. A revogação isolada não troca e-mail nem senha. |
| `admin_account.issue_email_verification`, `main.confirm_admin_email` | Troca comum por token verify_admin_email; confirmação revoga sessões e avisa endereço anterior | Não misturar com aprovação manual. O token comum não contém autoridade administrativa para recuperar conta. |
| `admin_security` | AES-GCM contextual, tokens com hash, expiração, consumo único e limpeza | Reutilizar primitivas, sem reutilizar propósito com efeitos diferentes. |
| `email_delivery`, `worker.validate_email_origin` | Outbox cifrado, vínculo com origem e destinatário, sem transporte externo nos testes | Novo atendimento precisa ser origem explicitamente validada pelo worker; não aceitar source arbitrário. |
| `platform_console.authorized` | Proprietário global, rechecagem na saída, tratamento sanitizado; operações sensíveis reautenticam | Novo início/consulta/confirmação owner-only. Sem recuperação do próprio PlatformOwner. |
| `tenant_closure_identity.confirm_identity_verification` | CPF correspondente + código do e-mail atual podem atualizar nome/e-mail e sinalizar verified após dez anos | Reconciliar antes de liberar nova recuperação: essa verificação não é autoridade independente para trocar acesso ou reabrir. |
| `tenant_closure_recovery` | Depois de dez anos consulta identidade verified; restauração e reabertura são separadas | Acrescentar vínculo com atendimento administrativo comprovado, sem retirada de suspensão ou contorno de exclusão de mídia. |

## Estruturas e restrições

`AdminActionToken.purpose` só admite password_reset/verify_admin_email. `AdminSecurityChallenge.purpose` tem enumeração própria. `PlatformAdminEvent.action` também tem lista fechada. Não forçar novos efeitos em propósitos existentes ou em ações de auditoria com nomes incorretos para evitar uma migration.

Um registro de atendimento próprio é necessário para ligar tenant, fotógrafo, proprietário, destinatário, versão da identidade, declaração externa, estado, expiração e replay. Identidade do proprietário é global, não pertence ao tenant alvo. Referências a fotógrafo/membership devem continuar tenant-scoped. Destinatário/token/material temporário precisam de proteção e limpeza, sem cópia de documento. Detalhes de schema serão definidos antes da implementação da task2.1.

## Consumidores adicionais obrigatórios

Uma nova tabela exige classificação em `ownership_schema`, inventário/guards de `homolog_cleanup` e `reset_homolog_owner`, além de migration, limpeza técnica e testes de constraints. Tratar qualquer atendimento como fonte protegida; não criar expurgo de auditoria por inferência. Migrations só em PostgreSQL descartável.

Frontend: `auth-entry.tsx` já oferece caminhos de recuperação; `admin/platform/page.tsx` hospeda atendimento por tenant e `photographer-totp-support.tsx` mostra recuperação existente. A rota nova de contato não deve ficar atrás do login que está sendo recuperado. Não expor token em consulta do proprietário nem no servidor/referrer do navegador.

## Avaliação proporcional de refatoração

Reutilizar autorização, cifras, validação de senha, outbox, invalidação e padrões visuais. Não remover os fluxos legados nem reformular autenticação global nesta change. Nenhuma limpeza funcional foi feita nesta leitura. Artefatos e nomes acima foram conferidos no código; o inventário não é prova de transporte real ou implementação da nova recuperação.
