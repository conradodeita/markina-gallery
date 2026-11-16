# Inventário de configuração — 03/11/2026

Task 1.2, somente fontes de código/documentação; nenhum valor de .env, token, chave, arquivo ou conteúdo remoto foi lido.

| Área | Evidência | Consequência |
| --- | --- | --- |
| Config Drive | Busca delimitada em `backend/app`, requirements, Compose e scripts não encontrou cliente/consumidor Drive. `GOOGLE_DRIVE_FOLDER_ID` era placeholder comentado no inventário inicial, não conexão operacional. | Não promover comentário a integração nem presumir credencial disponível. |
| Custódia existente | `integration_secrets.py`: envelope AES-GCM com versão de chave, nonce e AAD de ambiente + tenant + UUID da credencial; `INTEGRATION_SECRET_*` externos. `from_explicit_context` permite teste sem mudar env global. Limite atual de 512 caracteres por segredo ASCII. | Avaliar reutilização compatível para token Drive, sem alterar AAD legado, ler/reutilizar token MP, truncar material ou copiar configurações reais. Cliente OAuth/refresh token ainda não configurados. |
| Outras finalidades | `totp_crypto.py` e proteção facial têm contextos próprios. | Não usar chaves/secretos TOTP/biométricos como credencial Drive. |
| Autoridade | `PlatformOwner` por UUID e sessão/vínculo ativos; grants de monitor e instalação são técnicos. | OAuth/concessão/revogação de conexão global pertencem ao proprietário. E-mail Google ou path do Drive não concede papel SaaS. |
| Armazenamento | Compose usa raízes locais; prévias/miniaturas protegidas são locais por spec `media-storage/protected-previews`. Namespace e referências de mídia têm tenant persistido. | Drive permanece externo/privado, nunca CDN ou fallback de original; objeto remoto precisa de mapping autorizado, não apenas nome de pasta. |
| Entrega | `order_delivery.py` valida URL HTTPS fornecida pelo fotógrafo sem buscar o destino. | Preservar Google Photos/Drive manual por pedido; OAuth não automatiza álbuns ou compartilhamento. |
| Lifecycle | `improve-gallery-and-client-data-lifecycle` excluía arquivo frio; `add-gallery-media-archive` supersede somente a expiração automática, com task formal de reconciliação ainda aberta. | Não reutilizar exclusão explícita como arquivamento nem remover primário sem prova de recuperação. |
| Backup externo | Snapshot de 02/11 em `docs/saas-evolution/security-audit-2026-11-01.md` identifica timer/rclone crypt fora da aplicação; não é adapter SaaS. | Não ler/transferir credencial/cópia de backup existente nem interferir no outro projeto do host. Fonte nova exige autenticação e proveniência próprias. |

O proprietário confirmou **Google Workspace/organização** em 03/11. Quota efetiva, identidade OAuth, existência/acesso a Shared Drive e pasta de destino não foram autenticados. Aproximadamente 100 TB é premissa informada, não medição. Detalhes e próximos gates em design.md.

## Revisão de implementação local — 03/11/2026

`google_drive_oauth.py` exige `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, `GOOGLE_DRIVE_REDIRECT_URI` e `INTEGRATION_SECRET_*`; o OAuth externo real bloqueia fora de `APP_ENV=production`. O secret permanece em secret store/configuração segura, não em `.env.example`. Caminho de retorno implementado: `/api/admin/platform/drive/oauth/callback`. O proprietário confirmou que criou um cliente OAuth Web, status Enabled, em 03/11/2026; o executor não leu o JSON nem consultou ID/secret. A URL absoluta candidata `https://pickyourpic.com.br/api/admin/platform/drive/oauth/callback` ainda não teve o roteamento público confirmado: consulta DNS A/AAAA não retornou endereços e a requisição HTTPS falhou antes de resolver o host. `GoogleDriveOAuthAttempt` armazena digest de state e verifier cifrado; `GoogleDriveConnection` guarda somente envelope cifrado de refresh token. Nenhum valor secreto real foi consultado ou persistido.
