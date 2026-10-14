# Design

## Context

Veja `proposal.md` para a motivação e `specs/auth/spec.md` para o contrato. `ProtectedSession` monitora falhas de chamadas same-origin `/api/` e revalida em foco/retorno/visibilidade; a checagem periódica de segurança a cada 60 segundos é preservada. Antes desta change, a notificação temporária só mudava quando o botão chamava novamente `/api/auth/destination`. A verificação de sessão não repete as operações que falharam.

## Goals / Non-Goals

**Goals:**

- Recuperar automaticamente o estado visual quando a sessão volta a ser confirmada.
- Iniciar a tentativa de reconexão/revalidação sem ação manual do usuário.
- Retentar somente a leitura segura da sessão, com limite, espera progressiva e uma chamada em andamento por vez.
- Preservar os tratamentos existentes para sessão expirada e acesso negado.

**Non-Goals:**

- Reenviar automaticamente OTP, compra, upload, pagamento ou qualquer mutação.
- Alterar APIs/backend, lógica de autenticação, canais de comunicação ou deduplicação comercial.
- Prometer que uma resposta bem-sucedida de sessão confirma o resultado de uma mutação anterior; o fluxo da operação mantém sua própria reconciliação.

## Decisions

1. **Revalidar a sessão, não a operação que falhou.** Usar `/api/auth/destination` como sinal autorizado de conectividade e contexto. Uma chamada bem-sucedida confirma apenas que a sessão voltou; não prova que uma compra ou mensagem anterior foi concluída. Isso evita replay inseguro de efeitos comerciais. Alternativa descartada: retry automático da requisição original, pois timeout pode ocorrer depois de o servidor aceitar o efeito.
2. **Reconectar automaticamente com retry limitado, backoff e deduplicação.** Depois de falha temporária, iniciar verificações da sessão em segundo plano com atraso crescente de 1 s, 2 s, 4 s e assim por diante, limitado a 30 s entre verificações; continuar nesse teto até recuperar a sessão. Não esperar clique em botão “Reconectar” ou “Verificar conexão novamente”. Manter `pending` como single-flight, cancelar timeout e timer ao desmontar ou expirar e não executar probes enquanto a página estiver oculta. Ao voltar a ficar visível, fazer uma revalidação imediata. Preservar a revalidação de segurança a cada 60 s da spec vigente para detectar revogação sem interação; durante uma recuperação agendada, esse intervalo e erros de outras operações não antecipam o backoff. Foco/retorno visível continuam permitindo uma checagem imediata.
3. **Limpar o alerta no sucesso da revalidação.** Quando `/api/auth/destination` retornar destino compatível com a área atual, limpar o aviso temporário sem toast de recuperação nem clique. 401/403 mantêm seu tratamento atual. Alternativa descartada: limpar após qualquer API de negócio responder, porque uma resposta não relacionada não comprova a sessão nem o resultado da operação anterior.
4. **Separar falha de endpoint de perda de conectividade.** Uma resposta transitória de uma operação agenda a checagem segura da sessão; o aviso global só é apresentado se essa checagem também falhar. A falha específica permanece com o componente que iniciou a operação. Isso evita converter um erro isolado de endpoint em indisponibilidade de toda a plataforma. Alternativa descartada: mostrar o aviso global para qualquer 408/5xx mesmo com sessão confirmada.
5. **Remover a ação manual de reconexão.** Não exibir “Verificar conexão novamente” nem exigir clique em “Reconectar”; a função interna fica sob controle do ciclo automático. O aviso é informativo e não bloqueia o conteúdo quando a sessão já foi validada.

## Risks / Trade-offs

- [Tentativas automáticas aumentam carga durante indisponibilidade longa] → Backoff progressivo com teto, single-flight e pausa enquanto oculto.
- [O usuário pode interpretar a recuperação da sessão como confirmação de uma compra/envio anterior] → Não exibir “operação concluída”; preservar aviso específico do fluxo e documentar que a checagem só confirma sessão/conectividade.
- [Uma oscilação curta pode atrasar a indicação de indisponibilidade] → Confirmar o aviso somente após falha da checagem segura de sessão e preservar erros próprios da operação; revalidar novamente em backoff limitado.

## Migration Plan

Sem migration de banco ou mudança de API. Atualizar o componente e seus testes, executar validação frontend dirigida e OpenSpec. Reversão é o retorno ao comportamento anterior no frontend; nenhuma configuração externa muda.
