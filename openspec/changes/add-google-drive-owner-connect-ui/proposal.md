# Proposta: Interface de conexão do Google Drive do proprietário

## Contexto

O backend publicado já oferece OAuth owner-only com reautenticação, state de uso único, PKCE S256 e escopo `drive.file`. A tela Plataforma mostra o estado da conexão, mas não permite iniciar o fluxo; por isso o proprietário não consegue chegar à tela de consentimento sem um cliente HTTP improvisado.

O proprietário já autorizou iniciar a conexão da própria conta, pedir somente `drive.file` e parar na tela de consentimento Google para aprovação manual. Esta mudança fornece a interface necessária para cumprir essa autorização.

## Escopo

- Exibir, na seção Google Drive da Plataforma e somente quando não houver conexão ativa, um formulário de reautenticação do proprietário.
- Enviar senha e código TOTP diretamente à API same-origin, sem persistência local, telemetria, logs de cliente ou exibição em mensagens.
- Retornar ao frontend uma URL de autorização criada pelo backend e validada para o endpoint oficial do Google e o escopo exato `drive.file`.
- Redirecionar o navegador para o Google. A aprovação do consentimento continua manual e fora desta mudança.

## Fora de escopo

- Aprovar o consentimento Google, trocar token, observar quota, chamar outros endpoints Drive, configurar pasta, executar backup ou acessar arquivos/fotos.
- Alterar contas de fotógrafos, dados de clientes, autenticação geral, segredos, migrations ou configuração de produção.
- Implementar revogação ou reautorização de uma conexão já ativa.

## Resultado esperado

O proprietário consegue iniciar o fluxo OAuth pela interface autenticada, com nova confirmação de senha e TOTP, e o navegador chega à tela Google com escopo mínimo. A conexão permanece ausente até a aprovação manual e callback válido.
