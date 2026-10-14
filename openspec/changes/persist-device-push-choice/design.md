## Context
A inscrição pertence à instalação em cookie seguro e à identidade autenticada. Logout e troca de conta revogam a associação anterior. O frontend consulta apenas o estado do servidor, sem memória do consentimento e sem reconciliar PushManager.

## Goals / Non-Goals
Evitar cliques repetidos para reativar em acessos da mesma conta e oferecer convite inicial. Preservar controles de privacidade e limitações do navegador.

## Decisions
- Guardar somente enabled/disabled/dismissed em localStorage com chave versionada por identidade opaca (papel + UUID). Não guardar endpoint, chave, token, nome ou telefone. Falha do storage não bloqueia a ativação; preferência em memória é fallback da página.
- Estado ativo exige inscrição do navegador e associação autenticada do servidor. Associação já ativa migra a escolha para enabled. Ausência ou expiração da inscrição pode ser reparada para quem aderiu, somente com Notification.permission granted.
- Reutilizar inscrição existente compatível; não rotacionar a cada navegação. Serializar operações de dispositivo, inclusive logout, usando Web Locks quando disponível e fila local como fallback. Invalidar trabalho obsoleto na desmontagem/troca de rota e logout.
- Revalidar identidade antes do POST e enviar expected_identity para comparação no backend; o servidor continua escolhendo o dono exclusivamente pela sessão. Campo opcional mantém compatibilidade com abas antigas.
- Convite modal nativo acessível com Ativar avisos e Agora não; dispensa persistida. Solicitação nativa somente no clique. Negação ou ambiente incompatível não gera prompts automáticos. Desativação explícita impede restauração.
- Logout continua revogando inscrição e limpando notificações; conserva apenas a escolha. Reentrada da mesma identidade restaura quando possível. Uma identidade diferente precisa de sua própria adesão.
- Recuperação automática sem permissão, sem rede ou que exija gesto apresenta ação manual; não insiste em loop. Refoco permite nova conciliação.

## Risks / Trade-offs
Memória é específica à origem, conta e armazenamento do navegador/aplicativo. Limpeza de dados, navegação privada e outro dispositivo podem exigir nova ativação. iOS exige aplicativo na Tela de Início no fluxo suportado. Esses limites devem constar na ajuda e validação.

## Validation
Testar reload, logout/login, troca de identidade, opt-out, convite/dispensa, permissão negada, inscrição ausente, falha de rede, resposta obsoleta, concorrência e backend expected_identity. Verificação em aparelho real fica pendente do deploy autorizado.

Referências consultadas em 2026-09-20: [MDN requestPermission](https://developer.mozilla.org/en-US/docs/Web/API/Notification/requestPermission_static) e [WebKit Web Push em iOS](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/).
