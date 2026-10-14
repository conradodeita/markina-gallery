# Design

## Context

Ver `proposal.md` e `specs/auth/spec.md`. No fluxo atual, `/auth/client/challenge` persiste o desafio e enfileira o OTP antes da autorização contextual que hoje ocorre em `/auth/client/verify`. `invite_only` já exige associação ou convite compatível para acesso. A tela espera um `challenge_id` e apresenta a etapa de código; a resposta neutra também protege contra enumeração de telefone e vínculos.

## Goals / Non-Goals

**Goals:**
- Aplicar a autorização contextual antes de qualquer entrega WhatsApp, tanto no primeiro pedido quanto no reenvio.
- Manter compatibilidade do contrato HTTP e não revelar se telefone, cliente, vínculo ou convite existem.
- Permitir que uma cliente recém-vinculada use o desafio existente para solicitar uma nova entrega, sujeita à revalidação.

**Non-Goals:**
- Alterar a autorização final de fotos ou os modos `standard` e o legado `collective_protected`.
- Criar ou modificar vínculo, cadastro ou sessão durante a solicitação/reenvio do OTP.
- Alterar limites, expiração, provedor WhatsApp, banco, configuração ou deploy.

## Decisions

1. **Autorizar antes de enfileirar.** Resolver o contexto de galeria, a identidade correspondente ao telefone e a elegibilidade do vínculo/convite antes de chamar a outbox. Para `invite_only`, uma capacidade pública de localização, isoladamente, não basta. Vínculos devem estar ativos; convite individual deve estar ativo, dentro do prazo e destinado à mesma identidade telefônica. Convites individuais privados continuam limitados ao destinatário previsto na capacidade. O link `private_gallery_link` mantém seu contrato próprio de associação compartilhada, aprovado em `consolidate-shared-private-galleries-and-progressive-sales`, inclusive quando a origem pública é `invite_only`; ele não é um convite individual. A solicitação de OTP não cria associação.

2. **Preservar resposta neutra com desafio sem entrega.** Para contexto inelegível, responder como hoje e manter a etapa de código com um desafio que não corresponde a nenhum OTP enviado. Persistir um hash de segredo aleatório fora do formato de seis dígitos aceito pela verificação, sem criar registro de entrega nem colocar mensagem na fila. A verificação desse desafio não concede sessão nem acesso, mesmo que o cliente seja vinculado posteriormente; um reenvio autorizado substitui o segredo por um novo OTP. Essa opção mantém o contrato sem tornar observável a existência do cliente ou do vínculo por uma resposta HTTP diferente.

3. **Reavaliar no reenvio.** O reenvio recarrega a capacidade e o contexto, resolve novamente o telefone e consulta o vínculo vigente. Se continuar inelegível, retorna resposta neutra sem entrega. Se o fotógrafo vinculou o cliente após o pedido inicial, o reenvio gira o segredo e enfileira um novo OTP. Capacidade revogada/expirada ou vínculo removido bloqueia o envio mesmo que um desafio anterior permaneça ativo.

4. **Preservar fluxos fora do escopo restrito.** Sem contexto de galeria, `standard` e o legado `collective_protected` continuam seguindo os contratos existentes. Em `standard`, o cadastro/vínculo autorizado continua ocorrendo somente depois da comprovação OTP. Nenhum caminho novo concede acesso pela posse do link.

5. **Provar a fronteira na outbox.** Testes de integração verificam que requisição inelegível cria zero entrega, que elegibilidade válida cria exatamente a entrega esperada e que o estado alterado entre solicitação e reenvio é respeitado. Os testes também verificam equivalência da resposta neutra e ausência de sessão, vínculo ou cadastro prematuro.

6. **Preservar privadas após exclusão da origem.** A disponibilidade contextual no reenvio segue a mesma regra já aplicada na solicitação inicial: privadas habilitadas com capacidade válida continuam acessíveis em origem `active` ou `deleted`. A restrição da galeria pública não impede o acesso privado já autorizado.

## Risks / Trade-offs

- [Desafio sem entrega pode confundir alguém que não recebe código] → manter texto neutro já usado, orientar genericamente a conferir se possui acesso à galeria e garantir que o reenvio após vínculo emita um novo código.
- [Verificações duplicadas podem divergir da regra final de acesso] → centralizar ou reutilizar a mesma decisão de elegibilidade, com testes compartilhados entre solicitação, reenvio e autorização final.
- [Consulta de vínculo pode revelar diferença por tempo de resposta] → manter resposta/status/corpo uniformes e evitar consultas que variem conforme o estado além do necessário; validar a resposta observável nos testes.

## Migration Plan

Sem migration ou ação operacional prevista. Implementar e validar localmente, comparar outbox/respostas e fluxos autorizados, depois seguir o processo normal de revisão e CI. Qualquer deploy em homologação exige inventário e autorização próprios.

## Integração ao baseline multitenant

Integração sobre `origin/develop` em `25d362539f952591baff796bf756439dd9839966`, posterior ao checkout da primeira implementação. O telefone SHALL ser resolvido exclusivamente no tenant da capacidade/galeria; vínculo ou convite em outra conta com o mesmo telefone não concede elegibilidade. Preservar `client_link_context`, `client_challenge_context`, validação da conta/canal e reautenticação contextual existentes. Entrada anônima sem link válido continua negada; entrada sem contexto de galeria exige sessão própria. O modo coletivo legado continua bloqueado para navegação, sem conversão ou nova autorização operacional. Vínculo público precisa permitir navegação, inclusive o estado individual existente da cliente. Capacidade inválida/revogada/expirada preserva a rejeição neutra existente; não altera contrato HTTP do baseline.

O segredo sem entrega é escolhido antes de persistir o desafio, fora do formato aceito de seis dígitos. Reenvio bloqueado também gira o segredo e expira entregas técnicas pendentes segundo o contrato atual, preservando limites, tenant e minimização de PII. A atualização não cria vínculo nem sessão.
