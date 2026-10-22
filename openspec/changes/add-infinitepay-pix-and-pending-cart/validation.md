# Validation

## Contrato oficial e checkpoint anterior

Fontes oficiais verificadas em21/10/2026 (horário do proprietário):Central de Ajuda10766888,checkout-documentacao e página Checkout. Suportam cartão+PIX por link, single_payment, capture_method pix e consulta autenticada payment_check. A página Checkout anuncia taxa zero no PIX. Nenhum checkout real foi criado.

CI785/39707689448(head68c4f6a6) e CI786/39707743629(heada5a70f5e) confirmados completed/success antes desta change; corpos dos PRs atualizados. Esses resultados não aprovam código novo desta change.

## Task1.1

Migration0086 adiciona checkout_methods_snapshot com default legado credit_card,capture_method nullable com constraint e cart_dismissed_at nullable.4 testes PostgreSQL aprovados em61,12s:upgrade preserva identidades/estado/valor,legado fica crédito exclusivo sem inventar método;captura inválida recusada;downgrade sem uso aprovado;downgrade com mixed/capture/dismissed recusado. Ruff aprovado. Banco descartável isolado por fixture em PostgreSQL local15470,nuncaOracle.

## Task1.2

Regressão de emissão mista falhou antes da correção (2failed/1passed; snapshot só credit_card). Depois:20 casos de confirmação passaram no ensaio PG conjunto, incluindo PIX/cartão mistos idempotentes e PIX em legado rejeitado. O mesmo ensaio terminou45passes/2falhas HTTP por fixture que assumia APP_ENVdevelopment enquanto runner usa test; não era falha financeira. Fixture passou a declarar seu ambiente sintético explicitamente.29 testes HTTP finais aprovados em2,23s sob runner test (também29/0 em3,10s isoladamente). Payload deriva métodos do snapshot e guarda de capacidade continua antes do efeito. Nenhum endpoint/auth alterado.

## Task2.1 em validação

Webhook recebe somente candidato limitado16KiB/schema/rate-limit e consulta com credencial histórica; `webhook.url/events=[paid]` enviado no contrato atual. Helper de verificação reutilizado pelo retorno. Primeiro ensaio15casos:11passes/4falhas;3falhas de fixture sintética usavam verification_profile synthetic-only em compra infinitepay-public-v1, corrigida fixture explícita sem enfraquecer guard;1regressão do retorno repetido de compra já confirmada fazia consulta extra, corrigida preservando skip de consulta somente no retorno confirmado. Webhook continua verificando candidatos duplicados/concorrentes. Repetição em andamento; não marcar concluído antes do resultado.

Task2.1 concluída:15 testes PostgreSQL webhook+credenciais aprovados em96,40s,6avisos preexistentes. Inclui PIX/cartão reais da consulta apesar de payload forjado,mismatch,unpaid,unknown,erro/retry,schema/tamanho,eventos não solicitados,UUID inexistente,reabertura tardia e concorrência;6casos de cofre preservam credencial antiga após substituição. A consulta bloqueante foi deslocada para threadpool no webhook;repetidos concorrência/retry:2aprovados17,83s. Payload HTTP29/0,Ruff aprovado. Sem assinatura documentada,não afirmar autenticação do webhook;somente payment_check é prova neste fluxo.

## Task3.1

Regressão inicial falhou por ausência de payment_methods na projeção. Cinco testes PostgreSQL finais aprovados44,08s:mesmas3fotos/valor/URL,snapshot misto,ausência em Compras,cliente alheia/stale revision,desistência repetida/concorrente com uma auditoria,preservação integral de pedidos/itens/reservas e confirmação tardia PIX após esvaziamento. Uma primeira rodada4casos teve3passes/1erro de join ambíguo na fixture frozen;join explicitado,caso esvaziar repetido aprovado11,96s e matriz final5/0. A corrida confirmação/desistência admite200ou409conforme locks,mas sempre conserva confirmação e pedidos. Nenhum link remoto cancelado,reserva liberada ou foto restaurada.

## Task3.2

88 testes focados aprovados14,55s, incluindo novo checkout misto com fotos/valor/link originais, desistência confirmada/cancelada/conflito, estados creating/verification_required sem segunda emissão, rótulo PIX InfinitePay confirmado em Compras e ausência de decisão manual no painel. Textos de configuração distinguem integração mista do PIX manual; chave legada card_enabled mantém contrato, com rótulo de ativação do checkout inteiro. Links antigos sem snapshot PIX continuam descritos como cartão exclusivo.

Primeiro ensaio de UI apontou expectativas dos textos anteriores; atualizadas para a decisão aprovada. Erro de codificação em novos testes/scripts locais foi corrigido, preservando UTF-8. Nenhuma falha foi ocultada com skip. Suíte completa inicial:623passes/1falha de foco no teste facial existente, sem modificação naquele arquivo; arquivo isolado33/33 e repetição integral624/624(67arquivos,142,40s). ESLint0erros/34avisos;Ruff aprovado. Ajuste final de aviso evita encaminhar pendência do Carrinho para histórico vazio; regressão focada repetida na integração.

## Integração em andamento

OpenSpec1.14.0 strict/all:136itens aprovados. HTTP/relatório:31aprovados4,30s. Plano final passa a0086 conforme release-plan.md, sem alterar gates0084. CI785/786 continuam comprovando somente os heads anteriores; novo código ainda não foi submetido ao CI neste checkpoint. Matriz PostgreSQL integrada, build e revisão final permanecem pendentes até resultado efetivo.

Checkpoint22/10:build Next/TypeScript aprovado;50testes do Carrinho repetidos após ajuste final do aviso, aprovados. HTTP/relatório final35/35 em2,89s, incluindo rejeição de lista PIX-only/duplicada/vazia e origem própria do webhook. Quatro casos PG adicionais aprovados68,45s validam método real no painel/estatísticas para ambos os meios e isolamento/limpeza no schema0086;outro caso PG de limpeza atual aprovado15,80s. Política de escopo19/19 aprovada146,25s;caso adicional recusa0086 aprovado6,73s e política de workflow aprovada, com publication_candidate_ready=false/api_fora_do_escopo esperado. Scanner preventivo dos38arquivos novos/alterados:zero achados, com saída redigida. Nenhuma allowlist de release alterada.

Revisão encontrou contador de webhook revertido junto com falha externa:regressão reproduziu400/400/400 em vez de400/400/429. Persistência do contador antes da consulta corrige o limite sem alterar finanças. Dez testes PG do webhook aprovados85,03s após correção. Retorno não confirmado ainda apontava a Compras vazia:regressão5casos reproduziu3falhas/2passes;destino passa ao Carrinho para estado não concluído/indisponibilidade, mantendo confirmação/exceção em Compras. Repetição final registrada abaixo quando concluída.

## Integração local concluída — 22/10/2026

Matriz PostgreSQL integrada:142aprovados,7avisos,1315,64s(21m55s), cobrindo emissão, mínimo, confirmação, reabertura/visibilidade, cofre, migrations0085/0086, pendências e webhook. O processo começou antes dos ajustes finais de contador/destino; suas fronteiras afetadas foram repetidas separadamente:10webhook/0 após persistência do limite e12retorno+credenciais/0(79,53s) após destino corrigido, incluindo sucessos legados e snapshot da credencial antiga. Quatro casos de estatísticas/método/schema e um de limpeza foram repetidos em processos próprios, com schemas/databases sintéticos distintos. Sem Oracle.

Frontend:624/624 completos,50Carrinho repetidos após último aviso,build+TypeScript aprovados. HTTP/relatório35/35 finais. Ruff final aprovado;OpenSpec strict/all136/136 finais;diff sem erros de whitespace. Revisão proporcional manteve contratos legados, extraindo somente callback compartilhado e projeção/desistência da pendência;sem limpeza geral, novas dependências ou alterações do PR261. Gates de release não ampliados. Scanner preventivo sem achados;scanner de histórico e CI serão registrados no mesmo PR após commit/push, com SHA exato. Revisão humana e smoke autenticado/externo real continuam pendentes; testes sintéticos não comprovam pagamento real ou publicação.
