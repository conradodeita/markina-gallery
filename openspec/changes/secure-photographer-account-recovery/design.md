# Design

## Context

Ver proposal.md e mapa central. Encerramento, mídia e histórico existentes permanecem preservados. Decisão substitutiva do proprietário em10/11/2026: meios previamente validados primeiro; excepcionalmente, o proprietário julga a identidade fora do sistema e autoriza recuperação no console. Essa decisão substitui o bloqueio absoluto anterior quando todos os fatores foram perdidos. Não afirmar que o software comprovou a identidade externamente.

## Goals / Non-Goals

**Goals:** ação clara de recuperar acesso no detalhe do tenant, decisão administrativa auditável e uso prioritário dos meios anteriores.

**Non-Goals:** receber selfies/documentos, fazer reconhecimento facial, criar provedor SMS, apagar histórico, mudar retenção ou permitir reabertura automática de conta encerrada.

## Decisions

1. Nome/CPF identificam; não autenticam. A primeira orientação é usar recuperação existente com e-mail verificado e fatores anteriores válidos. Telefone só conta se já houver comprovação de controle, vínculo com aquele fotógrafo e mecanismo de recuperação disponível; número cadastrado, canal WhatsApp pareado ou telefone de cliente não servem por si só. Inventariar antes de anunciar esse meio como disponível.
2. Exceção manual: somente PlatformOwner, para fotógrafo SaaS alvo, declara explicitamente que verificou identidade fora do sistema e informa motivo. Não solicitar comprovação digital adicional ao tenant para essa exceção além do novo contato; a decisão de identidade é humana, não inferida por nome/CPF ou software. O SaaS não recebe fotos nem documentos e não armazena evidências externas.
3. Recuperar acesso será ação sensível no console: exigir senha/TOTP do proprietário, versão atual do alvo, confirmação explícita e idempotência. Novo e-mail precisa ser verificado antes da efetivação. Preservar endereço anterior até cumprir condições; recusar duplicidade ou alvo alterado. Não apresentar esse caminho como reset automático por CPF.
4. Reutilizar desafios, outbox cifrada, tokens de ação e serviços de recuperação/revogação existentes. O fotógrafo define a própria senha, sem enviá-la ao proprietário. Invalidar sessões e material de recuperação antigo aplicável. Revogação de fator perdido deve ser explícita; fatores ainda válidos não devem ser removidos indiscriminadamente. Definir a integração exata no inventário antes de código.
5. Registrar ator, alvo, motivo, decisão manual externa, resultado e instante, sem CPF, senhas, códigos ou documentos na auditoria comum. Prova de e-mail é vinculada ao atendimento e destinatário, curta e de uso único conforme mecanismos existentes; impedir replay, troca de conta/destinatário e confirmação com sessão revogada.
6. Recuperação de credenciais não altera lifecycle ou suspensão. Para conta encerrada, preserva gates de restauração/reabertura e revisão após dez anos; não restaura mídia excluída. Reconciliar o fluxo tardio existente para que CPF mais e-mail novo não sejam rotulados como comprovação independente. Atendimento da própria identidade PlatformOwner e contas legadas permanece em seus fluxos próprios.

## Risks / Trade-offs

- Engenharia social → proprietário assume a decisão de identidade; o software protege autorização, confirmação, contatos e auditoria, sem prometer eliminar o risco.
- Telefone não verificado → usar somente associação comprovada e mecanismo realmente existente; não presumir segurança pelo WhatsApp do tenant.
- Console simples virar atalho de acesso → distinguir recuperar credenciais, restaurar mídia, reabrir conta e retirar suspensão.
- Confundir planejamento e entrega → mapa central distingue implementação local em validação de publicação.

## Migration Plan

Implementação e testes somente locais após revisão dos artefatos. Inventariar consumidores e reaproveitamento antes de escolher schema; provar migration aditiva em PostgreSQL descartável se necessária. Não operar produção, credenciais ou transportes reais. Não modificar retenções; eventual política de dados de terceiros continua separada.

## Aplicação — decisões técnicas após inventário

O proprietário autorizou aplicar esta change em10/11. `inventory.md` identifica controles e limites. Criar registro dedicado `photographer_access_recovery`, sem inserir propósitos novos em tokens antigos nem fingir ações antigas da auditoria. Migration aditiva posterior0123, esquema congelado no arquivo de migration, integridade de target/tenant e classificação global do proprietário; incluir fonte protegida em ambas as limpezas legadas. Nenhuma limpeza real será executada.

Fluxo em três etapas: proprietário abre atendimento para alvo/version atual e declara identidade verificada externamente; fotógrafo recebe link de uso único no novo e-mail e define sua própria senha; proprietário confirma a efetivação com senha/TOTP atuais. A senha só existe em texto no POST secreto do fotógrafo; enquanto aguarda efetivação, guardar somente hash cifrado no material temporário. E-mail/senha antigos permanecem até a confirmação final. Reutilizar a janela de quinze minutos dos links administrativos, mostrada no acompanhamento; expirado exige novo atendimento. Repetição com mesmo identificador/corpo retorna o estado anterior sem enviar outro link; payload divergente recusa.

Pedido, alvo, ator e contexto permanecem para auditoria; token, destinatário e material temporário são apagados ao concluir ou expirar. Recusar e-mail já pertencente a outro AdminUser/candidatura; verificar antes e no commit usando os locks de identidade existentes. Falta de prova do novo e-mail não permite conclusão. A decisão final precisa de proprietário atual, declaração inicial e versão do alvo revalidada; nenhuma sessão é criada ao confirmar o link.

Fator perdido tem escolha explícita no atendimento. Se solicitada, revogação usa os controles existentes no commit final; caso contrário preserva TOTP. Sempre invalidar sessões e material antigo aplicável após efetivação, sem compartilhar senha com o proprietário. Caso de conta encerrada permanece encerrado e exige restauração/reabertura próprias.

O caminho público tardio de CPF/e-mail será reconciliado na task3.3: não conceder estado de identidade autorizada para reabertura sem vínculo ao atendimento administrativo efetivado ou comprovação anterior aceita. Não alterar esse caminho parcialmente enquanto o mecanismo de autorização ainda não estiver pronto. Ações com efeitos reais dependem dos gates de release existentes.

## Esclarecimentos operacionais confirmados em 10/11

Conta ativa com meios válidos utiliza primeiro o fluxo comum, sem aprovação do proprietário. Reset por e-mail mantém o segundo fator quando ativado; o link de e-mail sozinho não desativa TOTP. Quem consegue entrar com senha e TOTP pode usar a troca autenticada de e-mail já existente. Esta change não cria recuperação pública apenas por nome/CPF ou apenas por um código TOTP desvinculado de desafio.

Perda isolada do autenticador reutiliza `photographer_totp_support`: proprietário confirma motivo, senha/TOTP próprios; revoga fator, códigos e sessões, preservando senha e estado do tenant. Atendimento de e-mail/senha usa o registro dedicado e só aplica as credenciais juntas na confirmação final. Reabertura e retirada de suspensão continuam separadas, mesmo após recuperação de credenciais.

O gate tardio de reabertura consulta atendimento concluído ligado ao mesmo encerramento e ao e-mail atual do mesmo fotógrafo. O fluxo público de CPF/código não altera nome/e-mail sem essa autoridade. Não reutilizar verificações históricas antigas como autorização implícita.
