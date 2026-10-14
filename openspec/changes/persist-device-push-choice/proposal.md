## Why
O logout revoga corretamente o push, mas o sistema perde a escolha de adesão. A cliente precisa ativar manualmente a cada novo acesso, e não recebe um convite inicial de ativação.

## What Changes
- Memorizar adesão, desativação e dispensa do convite por identidade e navegador/dispositivo.
- Conciliar inscrição real do navegador com estado autenticado do servidor ao entrar, navegar ou retornar à aplicação; restaurar adesão previamente autorizada quando a permissão continuar concedida.
- Apresentar convite acessível de ativação a cliente/admin elegíveis sem repetir prompts para quem já decidiu.
- Manter revogação no logout e isolamento de contas; validar no backend a identidade esperada pela requisição de registro.

## Capabilities
### Modified Capabilities
- `messaging/web-push`: memória da escolha e restauração segura de inscrição.

## Impact
Componente compartilhado de push, contrato aditivo da API e testes. Sem migration nem mudança de chaves ou configuração de servidor.

## Non-goals
Não prometer entrega garantida, conceder permissão do navegador por código, compartilhar autorização entre aparelhos nem enviar notificações após logout explícito.
