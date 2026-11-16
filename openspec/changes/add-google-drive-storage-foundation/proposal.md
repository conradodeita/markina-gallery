# Proposal: Conexão segura com Google Drive

## Contexto

O requisito atual designa o Google Drive do proprietário como destino preferencial, sujeito à confirmação real de tipo de conta, autorização e capacidade. No código local não há cliente Drive, fluxo OAuth ou API de arquivos: `.env.example` contém somente o comentário `GOOGLE_DRIVE_FOLDER_ID`, e a entrega por pedido armazena um link HTTPS informado manualmente sem consultar o provedor. O Compose não declara serviço Drive.

## Goals

- Integrar o Drive pela API oficial, mantendo autenticação, upload e leitura no backend.
- Conservar a conta sob controle do proprietário e não presumir capacidade/quota nem acesso de conta de serviço.
- Guardar tokens de longa duração em armazenamento seguro do servidor, sem Git, frontend, logs ou tabelas comuns.
- Restringir operações ao namespace da aplicação e negar navegação cruzada entre tenants.
- Expor estado, fonte, instante e disponibilidade para que ausência de conexão ou quota desconhecida nunca pareça saudável.

## Non-goals

- Arquivar mídia, fazer backup da plataforma ou excluir/recuperar galerias; cada fluxo terá change e política próprias.
- Gerar links públicos, servir prévias ou originais de Drive, ou substituir a entrega manual de pedidos.
- Criar/compartilhar credencial ou alterar a conta do proprietário sem OAuth e ação humana explícita.

## Evidência e dependências

- `backend/app/order_delivery.py` valida e grava link externo fornecido pelo fotógrafo; não faz fetch/HEAD. `frontend/app/admin/payments/order-delivery.tsx` aceita Drive, Google Photos ou equivalente como entrega externa de uma compra.
- `docker/docker-compose.yml` monta volumes locais de mídia em API/worker e não declara serviço/conector Drive. O campo comentado em `.env.example` não é consumidor de configuração.
- A spec `media-storage/protected-previews` mantém prévias no storage local e não usa Drive como origem de entrega. Esse contrato permanece intacto.
- O documento de execução autoriza considerar a conta do proprietário, mas exige autenticação real para confirmar plano, capacidade e permissões; esses fatos não foram inspecionados nesta auditoria.

## Decisões confirmadas e gates restantes — 03/11/2026

- A conta é Google Workspace/organização; o projeto Cloud Pick-your-Pic existe e o proprietário ativou a Google Drive API. A audiência OAuth escolhida é **Interno**; o contato de suporte foi escolhido e o de notificações foi preenchido pelo proprietário.
- O proprietário decidiu que conexão, quota e operações Google reais serão validadas somente em produção. A implementação e os testes locais usam somente transporte sintético.
- A autorização local usa cliente Web, `drive.file`, redirect URI configurada, state/PKCE de uso único e refresh token cifrado. Isso não concede acesso real nem confirma que a conta tem quota disponível.
- O proprietário criou um cliente OAuth Web, reportado como Enabled em 03/11/2026. A URI candidata indicada foi `https://pickyourpic.com.br/api/admin/platform/drive/oauth/callback`, mas a configuração salva não foi relida. DNS e HTTPS do domínio raiz foram preparados depois da pré-checagem inicial: o domínio responde com TLS válido e um host 404 reservado, sem encaminhar a aplicação. O callback ainda não existe no runtime de produção. Armazenamento do client secret, consentimento Google e conexão real ainda não ocorreram. Evidência operacional em `operations.md`.
- Shared Drive versus My Drive, quota/permissões efetivas, custodiante e recuperação das chaves ainda dependem da autorização Google em produção. Não presumir acesso a arquivos existentes ou ao armazenamento informado como 100 TB.

Sem essas confirmações, a conexão externa permanece desconhecida; não executar chamada real de escrita, upload, leitura ou revogação por inferência.
