# Preparação do Google Workspace — 03/11/2026

## Estado confirmado e limite

O proprietário confirmou conta Google Workspace/organização, criou o projeto Cloud **Pick-your-Pic** e ativou a **Google Drive API**. A audiência OAuth foi configurada como **Interno**; o contato de suporte foi escolhido e o e-mail de notificação foi preenchido pelo proprietário. O proprietário confirmou que criou um cliente OAuth Web em 03/11/2026 às 21:11 (GMT-3), com status **Enabled**; o Console ofereceu baixar o JSON. O executor não baixou nem leu o JSON, e nenhum ID/secret foi persistido. A capacidade aproximada de 100 TB é declarada, ainda não observada pela API. Shared Drive, permissões, quota disponível e custódia de credenciais não foram confirmados.

## Estado da preparação

**Estado mais recente, 03/11 aproximadamente 22:14 (GMT-3):** DNS e HTTPS raiz concluídos. Certificado exclusivo npm-4 e 404 Host 1 configurados pelo painel NPM autenticado; HTTP redireciona para HTTPS, que responde 404 de propósito enquanto a aplicação aguarda release. O domínio `markina` continuou respondendo 200. O backend OAuth ainda não existe na API publicada; schema remoto 0090 e cadeia local até 0098 exigem preparar rollout TOTP e release revisado. Não iniciar OAuth nem configurar segredos ainda. Detalhes em `openspec/changes/add-google-drive-storage-foundation/operations.md` e `release-readiness.md`. As falhas DNS/TLS descritas nos checkpoints anteriores foram resolvidas.

**Atualização posterior, 03/11 às 22:04 (GMT-3):** o proprietário definiu o mesmo Oracle como hospedagem. Foi salvo no Registro.br o registro A do domínio raiz para `132.145.193.169`, preservando `markina.pickyourpic.com.br`; o Google Public DNS já confirmou o novo A. A pré-checagem HTTPS do host raiz nesse IP falhou na negociação TLS, enquanto o host `markina` retornou HTTP 200. A ausência de DNS descrita abaixo corresponde à checagem anterior e foi resolvida. O próximo gate é inventariar e preparar proxy/certificado do host raiz e publicação do backend sob autorização operacional específica. Nenhum proxy, certificado ou secret foi alterado nesta configuração DNS.

1. Projeto, Drive API, branding e audiência interna foram configurados. O proprietário já preencheu o e-mail de suporte e o de notificação no Console. Não é necessário repetir esses passos.
2. O backend local implementa `/api/admin/platform/drive/oauth/callback`, mas ainda não está publicado. O Nginx versionado reescreve `/api/...` para o FastAPI; isso não confirma o roteamento ativo de produção. Consultas ao DNS público em 03/11 não retornaram registros A/AAAA para `pickyourpic.com.br`, e a requisição HTTPS de pré-checagem falhou na resolução do host antes de chegar ao servidor.
3. O cliente OAuth **Aplicativo da Web** já foi criado pelo proprietário e está **Enabled**. A URI candidata indicada foi `https://pickyourpic.com.br/api/admin/platform/drive/oauth/callback`, mas a configuração salva não foi relida e o domínio não resolve publicamente neste teste. Quando o hostname ativo for conhecido e o roteamento verificado, alinhar a URI no cliente e em `GOOGLE_DRIVE_REDIRECT_URI`. Não conceder consentimento nem fazer chamadas reais fora do procedimento de produção. [Guia oficial de credenciais](https://developers.google.com/workspace/guides/create-credentials).

Não enviar senha, client secret, JSON de credenciais, token ou códigos de autorização no chat. A configuração segura do servidor só ocorrerá sob autorização explícita e sem alterar `.env` por inferência.

## Etapa seguinte da implementação

O contrato OAuth local está implementado em `add-google-drive-storage-foundation`: `drive.file`, state/PKCE, revogação, envelope cifrado e consulta mínima de quota. A validação real em produção exige cliente OAuth, callback roteado, consentimento do proprietário, destino explicitamente escolhido e aprovação operacional específica. Não presumir acesso aos backups já existentes. [Escopos oficiais do Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth).

O ensaio posterior terá arquivo sintético e autorização própria. Previews continuam locais, entrega manual permanece preservada e o console informa estado desconhecido até haver uma fonte autenticada. Configurar o projeto Google não publica o SaaS nem autoriza deploy, upload de fotos ou remoção de dados.
