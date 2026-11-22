# Proposal

## Why

A plataforma ainda depende de provisionamento offline para criar contas de fotógrafos e não oferece cadastro público, verificação de e-mail e ativação automática segura. O portal permitirá ampliar o produto somente depois que isolamento, segurança, créditos e administração global passarem pelos gates anteriores do roadmap.

## What Changes

- Criar candidatura pública de fotógrafo com nome do fotógrafo, e-mail e OTP de uso único, com expiração, limites e resposta que não permita enumeração; persistir o nome no perfil do tenant após verificação e ativação.
- Decisão substitutiva do proprietário em 03/11/2026, refinada em `add-progressive-photographer-onboarding`: ingresso pelo website e ativação automática depois de verificar o e-mail e definir senha, sem aprovação manual. TOTP é opcional no início; após ativá-lo, será exigido nos logins seguintes, conforme os controles de recuperação aprovados.
- Após OTP, usar uma sessão de configuração restrita e de uso único para definir senha; provisionar tenant finito sem saldo e vínculo somente na conclusão atômica. A configuração voluntária de TOTP ocorre depois, em Configurações. Expirar/cancelar revoga desafios sem criar acesso.
- A automação nunca concede propriedade global, grants técnicos ou saldo artificial. O proprietário conserva a gestão comercial e a suspensão explícita.
- Aplicar proteção anti-bot server-side com Cloudflare Turnstile, aprovada pelo proprietário em 07/11/2026; não ativar o portal em produção sem configuração segura e domínio `pickyourpic.com.br` validado com titularidade, DNS e TLS.
- Não reutilizar nome, e-mail, CPF ou outros dados do checkout de clientes para o cadastro; revisar propósito, transparência, retenção e necessidade antes de ampliar a coleta além do nome informado pelo fotógrafo e e-mail.
- Decisões do proprietário em 11/11/2026: não expurgar automaticamente nome e telefone do perfil operacional de cliente somente por inatividade ou ausência de galeria acessível; preservar o fluxo explícito e auditado existente quando não houver histórico comercial protegido. Para pedidos, pagamentos e compras, a primeira versão não terá expurgo automático: manter somente os dados necessários sob os controles de acesso existentes. Eventos de auditoria (`AuditEvent` e `PlatformAdminEvent`) também não terão expurgo automático por enquanto e terão acesso restrito. Essas regras são temporárias; duração e exceções finais permanecem para decisão futura e não estabelecem retenção permanente. Logs técnicos, dados biométricos e atendimento a pedidos de titulares seguem políticas próprias.
- Manter cliente final e conta de fotógrafo em entidades, papéis, OTPs e sessões separados.
- Decisão do proprietário em 07/11/2026: clientes menores continuam usando o fluxo existente de galeria, seleção e compra sem vínculo geral obrigatório de responsável; fotógrafos/tenants devem ser adultos e confirmar essa condição no cadastro. A confirmação é declaração do candidato, sem coleta de data de nascimento ou documento e sem alegar verificação independente.

- Conforme decisão substitutiva do proprietário em 11/11/2026, exigir aceite eletrônico explícito e obrigatório dos Termos operacionais somente para novos uploads. Criação da conta, exploração, configuração e compra de créditos não dependem do aceite; a compra mantém e-mail verificado, CPF/endereço e controles financeiros próprios. O proprietário poderá editar rascunhos e publicar versões explicitamente, com protocolo imutável; a primeira versão não depende de revisão jurídica. Identidade e contato do provedor usam somente os dados confirmados pelo proprietário e a política de retenção aprovada.

## Capabilities

### Modified Capabilities

- `photographer-onboarding`: ampliar a capability existente com candidatura pública e ativação após verificação/senha; exigir Termos apenas para novos uploads, sem bloquear compra de créditos.
- `auth`: incluir verificação inicial por e-mail e conclusão segura de senha, com TOTP opcional para a conta criada pelo website e sem alterar o OTP de cliente, o proprietário da plataforma ou contas legadas.
- `billing/mercadopago-credit-purchases`: exigir e-mail verificado, perfil completo e controles financeiros próprios, sem condicionar a compra ao aceite dos Termos.
- `tenant-foundation`: substituir a proibição futura de cadastro público por ativação controlada, mantendo o portal desabilitado até os gates prévios e nunca criando tenant ativo antes de verificar e-mail e definir senha; não exigir TOTP ou Termos para a ativação exploratória.

## Impact

Aceite contratual progressivo exigido para novos uploads; compras de créditos seguem perfil/e-mail e controles financeiros próprios. Template preenchido somente com dados autorizados do fotógrafo e do provedor; protocolo imutável no histórico do proprietário e cópia disponível ao fotógrafo.

Frontend público; APIs e persistência de candidaturas/desafios com nome e e-mail; envio de e-mail; integração anti-bot configurável; provisioning de `AdminUser`, `Tenant` e `TenantAdmin`; auditoria de ativação e consulta owner-only do cadastro; migrations e testes de abuso, enumeração, replay, expiração, separação de papéis e isolamento. A change depende da conclusão/aceite das fases R14-0–6, incluindo a segurança do `PlatformOwner`, piloto multi-tenant, carteira/créditos e console do proprietário; TOTP do fotógrafo permanece opcional no ingresso conforme a decisão posterior. Domínio, provedor anti-bot, retenção legal e qualquer dado adicional permanecem gates externos; não autoriza deploy ou ativação de produção.

## Prova local autorizada em 03/11/2026

O proprietário priorizou backend e prova de fluxo com uma interface simples, antes do design definitivo. É permitido implementar e testar o cadastro isolado com contas sintéticas e transporte de e-mail simulado; isso não autoriza publicar o website, enviar e-mails reais ou antecipar os Termos de lançamento. Os gates R14 e externos continuam obrigatórios para ativação remota.
