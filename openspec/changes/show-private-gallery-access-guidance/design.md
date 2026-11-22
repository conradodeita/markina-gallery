# Design

## Context

Veja `proposal.md`. `/auth/client/challenge` já mantém respostas neutras e suprime a entrega de OTP quando não há vínculo ou convite elegível. Hoje a tela interpreta toda resposta aceita como etapa de código, mesmo quando o desafio não entregará OTP.

## Goals / Non-Goals

**Goals:**

- Mostrar o estado privado antes do campo OTP em qualquer autenticação contextual a `invite_only`.
- Manter idêntico o marcador e o aviso para todos os telefones do mesmo contexto.
- Preservar a ação explícita de continuação para clientes legitimamente convidadas e não modificar a autorização do servidor.

**Non-Goals:**

- Não consultar se um telefone existe ou está vinculado para decidir a interface.
- Não alterar elegibilidade, envio/reenvio, expiração, rate limit, criação de sessão ou resposta de autenticação.
- Não tornar públicas informações de cliente, título de galeria ou dados do fotógrafo.

## Decisions

1. **Derivar o marcador somente do modo contextual.** A resposta de `client_challenge` inclui `show_private_gallery_notice: true` quando a galeria resolvida está em `invite_only`, em caminhos com ou sem capability. O marcador é calculado sem consultar o telefone ou o resultado de elegibilidade; a resposta não inclui cadastro, cliente, convite ou motivo de supressão. Respostas para `standard` e contexto inválido mantêm o fluxo atual.
2. **Usar uma etapa intermediária, não uma resposta de erro.** Em `invite_only`, a UI mostra “Esta galeria é privada. Para acessar, peça ao fotógrafo um convite individual.” e oculta o campo de código. O botão “Já tenho um convite” abre o formulário OTP e mostra a orientação neutra já existente. Assim, a cliente convidada mantém a reautenticação e uma pessoa sem convite não vê um campo que provavelmente não poderá usar.
3. **Manter o backend como autoridade.** Mesmo após a ação de continuação, a emissão e verificação continuam subordinadas aos vínculos/capabilities, guards e rate limits atuais. A affordance da tela nunca concede acesso nem permite cadastro contextual.
4. **Não persistir estado adicional.** O marcador pertence somente à resposta da solicitação; não requer migration, cookie, localStorage ou novo endpoint.

## Risks / Trade-offs

- [Uma cliente convidada precisa de uma ação extra antes de informar OTP] → usar CTA claro e permitir o retorno direto à etapa de código, mantendo o acesso atual.
- [O marcador revela que a galeria contextual é `invite_only`] → essa classificação é a informação que a tela precisa apresentar; o valor não depende de telefone, vínculo ou identidade, e nenhum dado adicional da galeria é retornado.
- [Uma visitante pode escolher continuar sem possuir convite] → o backend ainda suprime a entrega e rejeita a sessão sem revelar elegibilidade.

## Migration Plan

Nenhuma migration. Alterar o shape da resposta de desafio, adaptar a tela e cobrir equivalência de orientação para telefones autorizados e não autorizados. Rollback de código remove a etapa intermediária sem tocar em desafios ou dados persistidos.
