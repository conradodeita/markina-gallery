# Design

## Context

Motivação em proposal.md. O SessionBoundary usa key=pathname e recria ProtectedSession em cada rota, reiniciando authorized. O develop atualizado já inclui recuperação automática com backoff (d6df74f), removendo notice temporário após confirmação. Esse avanço será preservado. A mensagem de falha de leitura ainda presume incerteza de mutação, e falha de mutação com sessão saudável perde sua orientação. O monitor reúne dados técnicos e operacionais; a exportação vem de build_report e é independente da renderização. Texto exportado contém JSON com cabeçalho, sem narrativa humana.

## Goals / Non-Goals

Dicas nos seis blocos escolhidos, dados técnicos nos relatórios, feedback de sessão preciso e cores de atividade. Sem modificar backend, cookies, permissões, duração de sessão, histórico coletado, motores faciais ou dados reais. Nenhuma alegação de presença física ou capacidade máxima.

## Decisions

- Dicas nativas details/summary com nome acessível específico, toque/teclado e explicações breves. Nenhuma biblioteca ou tooltip apenas por hover. Seções Aplicação/experiência e Qualidade/coleta deixam a tela principal; fontes/atualidade/lacunas continuam visíveis nos blocos existentes. Relatórios continuam no mesmo endpoint/formato e passam a ser rotulados como técnicos.
- Árvore conserva label por e-mail e UUID interno; estilizar só o botão de identificação com data-activity, estado textual preservado. Verde para active (janela atual configurada de interação), vermelho para inactive (sem sessão válida com fonte atual), neutro para demais estados. Não ampliar coleta/polling de presença.
- Fronteira estável por protectedContext, sem reutilizar autorização entre admin/client ou público. Gate inicial preservado; efeito de pathname continua revalidando na mudança de rota sem reiniciar authorized no mesmo papel. Retentativas de leitura existentes continuam com backoff e pausa em aba oculta, sem replay; indicador interno de verificação prévia permite observar recusas de API durante revalidação pendente. Não criar armazenamento de credenciais ou cache persistente de autorização. O backend continua validando cada pedido.
- Separar aviso temporário de leitura da incerteza de mutação usando o método efetivo (Request ou RequestInit), excluindo o sinal automático POST /api/auth/activity dessa semântica comercial. Revalidação 200 limpa aviso de leitura; incerteza de escrita permanece como status recuperado com orientação de conferir resultado e ação explícita de fechar o aviso. Cleanup/cancelamento intencional não vira falha. 401, 403, papéis errados, timeout, deduplicação/follow-up e ausência de replay preservados.

## Risks / Trade-offs

Autorização indevida por reutilização → chave por papel, gate inicial e testes de troca/negação. Falha real mascarada → manter aviso quando há erro e retirar somente após 200 válido. Resultado de compra presumido → persistir orientação após falha de mutação. Cor confundida com presença → neutros e estados textuais/hint. Regressão em Gemma → preservar workers/coletores/exportação e ajustar expectativa somente da tabela técnica retirada.

## Migration Plan

Sem migration/configuração. PR develop, CI e deploy autorizados pelo fluxo vigente; pausar durante CI. Homologação autenticada somente no servidor: dicas, cores, foco, navegação e arquivos exportados. Não fabricar sessão, capturar cookie ou executar carga. Reversão pelo fluxo Git/deploy existente.
