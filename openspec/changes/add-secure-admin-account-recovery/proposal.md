## Why

O administrador hoje depende da senha e do TOTP já configurados, mas não possui um fluxo seguro de recuperação nem controles autenticados para atualizar e-mail e senha. A mudança completa esse requisito obrigatório de segurança sem transformar WhatsApp ou e-mail isoladamente em credencial suficiente para assumir a conta.

## What Changes

- Adicionar `Esqueci minha senha` à entrada do fotógrafo, com resposta neutra, rate limit e confirmação por OTP no WhatsApp administrativo verificado antes de enfileirar o link para o e-mail cadastrado.
- Adicionar redefinição por token opaco, de uso único, armazenado somente como hash, com expiração curta e invalidação após consumo ou nova solicitação.
- Revogar sessões administrativas após a redefinição e exigir novo login completo com senha e TOTP; o link de recuperação não criará sessão administrativa.
- Adicionar em `Configurações` a troca autenticada de senha e de e-mail, ambas confirmadas por OTP no WhatsApp verificado e auditadas.
- Manter o e-mail atual ativo até a confirmação do novo endereço por link de verificação; notificar o endereço anterior sem expor tokens ou segredos.
- Introduzir um `EmailProvider` substituível e uma caixa de saída durável para e-mails transacionais de recuperação, verificação e avisos, com adaptador sandbox seguro e SMTP configurado exclusivamente por segredo de ambiente.
- Preservar respostas neutras, proteção contra enumeração, política forte de senha e invalidação concorrente de tokens/desafios.

## Capabilities

### New Capabilities

- `messaging/email-transport`: entrega transacional de e-mails por adaptador, caixa de saída durável, observabilidade sanitizada e configuração SMTP segura.

### Modified Capabilities

- `auth`: recuperação segura da conta administrativa e alteração autenticada de e-mail e senha em Configurações.

## Impact

- Backend FastAPI/SQLAlchemy/Alembic: novos desafios e tokens, caixa de saída de e-mail, endpoints públicos neutros e endpoints administrativos autenticados, revogação de sessões e auditoria.
- Worker: processamento e retentativas da caixa de saída por `EmailProvider`, sem envio de rede no ciclo HTTP.
- Frontend Next.js: fluxo `Esqueci minha senha`, página de redefinição e seção de segurança da conta em `Configurações`.
- Operação: novas variáveis documentadas sem valores secretos, escolha/configuração posterior do SMTP transacional e validação externa de SPF, DKIM e DMARC antes do uso real.
- Testes: segurança, concorrência, expiração/uso único, não enumeração, autorização, revogação de sessões, acessibilidade e estados de interface.
