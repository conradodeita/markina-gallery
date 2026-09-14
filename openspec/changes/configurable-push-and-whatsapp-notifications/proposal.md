## Why

Fotógrafo e cliente precisam receber avisos curtos das etapas da galeria sem manter a página aberta. A página atual de Notificações é uma lista de eventos de acesso, enquanto os textos de pagamento estão separados em Configurações e não há Web Push implementado.

## What Changes

- Entregar notificações transacionais em WhatsApp e push com interruptores independentes por evento/destinatário e textos globais personalizáveis por canal.
- Cobrir seis eventos: primeiro login OTP por cliente/galeria e primeira seleção nessa galeria para o admin; novas fotos privadas com prévias disponíveis para clientes vinculados; pagamento informado para o admin; confirmação e recusa para o cliente do pedido.
- Agrupar novas fotos em um aviso por lote, sem disparo por foto ou espera pelo reconhecimento facial/ajuste opcional.
- **BREAKING**: substituir a listagem de `/admin/notifications` pela central de configuração. Mover Mensagens de pagamento de Configurações, preservando textos e histórico técnico; atualizar links contextuais para a nova central.
- Oferecer ativação/revogação de push por dispositivo para admin e cliente, com permissão explícita e estados claros de suporte/bloqueio.
- Não reenviar eventos antigos ao ativar canal ou editar template; retentativas e canais não alteram os estados de negócio.

## Capabilities

### New Capabilities

- `messaging/transactional-notification-settings`: matriz de seis eventos, canais, templates e nova central administrativa.
- `messaging/web-push`: inscrições autenticadas, entrega durável, revogação, privacidade e navegação autorizada.

### Modified Capabilities

Nenhuma spec principal de messaging foi consolidada. Esta change complementa as changes ativas de WhatsApp/pagamento e substitui explicitamente apenas a obrigatoriedade da antiga listagem de notificações e os disparos externos sobrepostos. Não criar deltas MODIFIED apontando para specs principais inexistentes.

## Impact

Backend de OTP/seleção/importação/pagamento, modelos e migrations aditivas, filas de mensagens, serviço Web Push, service worker, controles compartilhados e páginas administrativas. Novas chaves de push ficam exclusivamente no servidor; nenhuma credencial será criada ou alterada durante o planejamento. Preservar regras financeiras, autenticação e mensagens de OTP/recuperação/convite/reabertura/busca facial fora destes seis eventos.

`persist-branding-assets-across-deploys` continua pendente e não é cancelada nem incorporada silenciosamente. Sua persistência e os arquivos oficiais de ícone são pré-requisitos para aceite visual/instalação real, não para testes locais de push. Antes da implementação, reconciliar essa dependência conforme a sequência do repositório; não declarar PWA concluído com ícones 404. A adaptação de imagens até 10 MB discutida anteriormente não está incluída nesta change.
