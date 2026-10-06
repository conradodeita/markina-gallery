# Design

## Context

A notificação atual contém somente o caminho direto da galeria. O limite observado está na entrada OTP: sem sessão, ela exige um token de capability para resolver o fotógrafo. A API de galeria já valida cliente + galeria e carrega a busca mais recente após autenticação. Ver `proposal.md` e os deltas em `specs/`.

## Goals / Non-Goals

**Goals:**

- Reabrir o formulário de cliente com retorno à galeria em sessão ausente/expirada.
- Autenticar novamente apenas um cliente já vinculado e ativo na galeria indicada.
- Evitar token de capability, resultado facial e PII no link da notificação.
- Revalidar galeria e vínculo nas fronteiras do ciclo OTP.

**Non-Goals:**

- Alterar emissão, rotação, consumo ou prazo de convites/capabilities existentes.
- Criar registro de cliente, vínculo ou autorização a partir da notificação.
- Forçar nova autenticação quando a sessão e o vínculo já são válidos.
- Modificar prazo ou renovação das sessões.

## Decisions

### Link de retorno usa rota interna estrita

A mensagem apontará para `/?reauth=client&return_to=/public-galleries/{uuid}`. `recoveryLocation` preservará esse destino para rotas de galeria válidas. Frontend e backend aceitarão como contexto de recuperação somente o caminho exato de uma galeria pública com UUID válido; caminhos externos, administrativos, com query ou segmentos extras não selecionarão contexto.

Alternativa rejeitada: incluir `access_token` no WhatsApp. A capability pública é um bearer link reutilizável e pode iniciar cadastros em galeria padrão; copiá-la para a notificação ampliaria a circulação dessa autoridade desnecessariamente.

### Reautenticação sem convite exige vínculo prévio

A challenge pode incluir `parent_gallery_id` somente no retorno contextual. A API resolve a galeria ativa e seu tenant; esse identificador é um seletor, nunca prova de autorização. Antes de criar/reenviar OTP e novamente antes de validar o código, a API resolve telefone dentro do tenant, confere registro ativo e estado cliente/galeria não bloqueado. O fluxo existente de verificação já revalida acesso à galeria quando o desafio contém `parent_gallery_id` e não há capability; somente essa variante de desafio será admitida sem sessão.

Para números sem acesso, a resposta externa e a forma da transição permanecem neutras, sem entrega OTP, sessão ou cadastro. O ID de desafio opaco sem registro, se usado para manter a resposta uniforme, não permite consulta, reenvio ou verificação válida.

Alternativas rejeitadas: tornar `/public-galleries/{uuid}` suficiente para enviar OTP a qualquer telefone (facilitaria envio abusivo) e permitir login genérico sem sessão/token (perderia resolução inequívoca de tenant).

### Sessão existente vai direto ao retorno interno

Quando o cliente já possui sessão, a entrada contextual navegará ao retorno interno exato; as APIs da galeria continuam como autoridade e recusam sessão de outro cliente, tenant suspenso, galeria inativa ou vínculo revogado. Para sessão ausente, a tela permanece no contexto Cliente e inicia OTP contextual.

### Resultado continua vindo da API autenticada

O link não carrega identificador de busca. Ao abrir a galeria, o componente existente solicita availability/latest com cookie da sessão, e o backend escopa o resultado ao `client_id` da sessão e à galeria. A tela não inicia outra consulta se nenhuma busca vigente existir.

## Risks / Trade-offs

- [ID de galeria compartilhado] → é somente seletor; não cria sessão nem entrega OTP a cliente sem vínculo ativo, e a autorização é repetida na verificação.
- [Vínculo revogado enquanto OTP está em trânsito] → reenviar e verificar reconsultam estado vigente e falham fechados.
- [Conta legítima sem vínculo ativo] → não recebe OTP por este caminho; deve usar o convite autorizado original ou pedir ao fotógrafo que restaure o vínculo.
- [Sessão válida de outra cliente no mesmo navegador] → tentativa segue ao destino, mas APIs existentes recusam os dados; nenhuma autorização é inferida no frontend.

## Migration Plan

Não há migration nem mudança de configuração. A publicação depende do fluxo normal de CI/deploy protegido do repositório. Rollback de código restaura os links anteriores, que continuam protegidos por sessão e autorização; nenhuma capability ou sessão existente é alterada.
