# Plano de ativação em homologação — pendente de autorização

## Inventário confirmado em 17/10/2026

- Checkout publicado: `4342a3669e031500242f87424be0dbda21b5781b`; schema `20261017_0083`.
- Projeto Compose: `markina-gallery`, em `/opt/markina-gallery`; domínio `markina.pickyourpic.com.br`, entrada `127.0.0.1:8080`.
- API, web, worker geral, workers faciais e auxiliares saudáveis; `/api/health` respondeu `ok`.
- API e worker têm `TRANSACTIONAL_WHATSAPP_ENABLED=false`.
- Nos três eventos controlados pelo gate, WhatsApp está ativo somente para `private_photos_ready`; `first_access` e `first_selection` estão desativados no painel.
- O lote de seis fotos gerou aviso cancelado em `transport_disabled`, sem tentativa. Ele não será reaberto nem duplicado.

## Sequência proposta após CI verde e autorização explícita

1. Repetir inventário de SHA, saúde, serviços e configurações dos três eventos. Confirmar ausência de alteração concorrente.
2. Com autorização específica para configuração, alterar exclusivamente a variável não secreta `TRANSACTIONAL_WHATSAPP_ENABLED` para `true` na configuração persistida de homologação. Preservar todas as outras linhas/credenciais; nunca imprimir o arquivo completo.
3. Integrar a PR #218 somente após checks verdes. Usar o deploy automático de homologação já autorizado, com backup, preflight, migração inalterada e healthchecks. O processo existente substitui containers Markina e inclui parada controlada de escritores; não prometer disponibilidade ininterrupta durante essa janela.
4. Verificar explicitamente worker geral saudável, porta/subdomínio, flag na API/worker, SHA e schema. Conferir ausência de erro de persistência/processamento. A fila OTP persistida não será editada, apagada ou reenviada.
5. Pedir novo OTP pelo fluxo normal e um novo lote privado sintético/teste autorizado. Conferir geração, autorização e envio único do novo evento, além do recebimento informado pelo proprietário.

## Impacto e recuperação

O código altera somente o contrato de identidade do aviso e sua leitura. Não altera autenticação, ciclo do worker, política de restart, schema ou segredos. A ativação permite novos avisos configurados dos três eventos; os dois desativados no painel continuam desativados. Outros canais e transportes preservam seus gates.

O deploy pode causar indisponibilidade breve da aplicação/consumidor OTP durante a substituição dos containers. Se o worker não recuperar saúde, interromper a liberação e seguir o rollback protegido do deploy; nunca repetir restarts em laço. Se o código estiver saudável mas a ativação tiver problema, reverter somente o gate para `false` e aplicar a configuração aos serviços Markina afetados após inventário; preservar todas as filas. Não tocar na Evolution compartilhada, containers de terceiros, redes, volumes, proxy, firewall, DNS ou certificados.

## Estado

Plano preparado; autorização para modificar configuração ainda não recebida. PR #218 em CI, sem auto-merge habilitado nesta preparação. Nenhuma alteração remota executada.
