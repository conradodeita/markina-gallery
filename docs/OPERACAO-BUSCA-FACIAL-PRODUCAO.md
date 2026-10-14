# Operação da busca facial em produção

## SLOs e limites iniciais

Estes limites são gates de rollout, não promessa de precisão biométrica. As janelas usam somente eventos técnicos agregados e MUST NOT incluir IDs de galeria, cliente, request ou foto, imagem, embedding, score, landmarks, caixa facial, nome inferido ou telefone.

| Sinal | SLO/limite inicial | Janela e ação |
| --- | ---: | --- |
| Admissões aceitas quando o runtime está saudável | ≥ 99,0% | 24 h; abaixo disso, interromper promoção e investigar backpressure |
| Duração p95 de consulta aceita | ≤ 120 s | janela móvel de 1 h sob carga de até 100 clientes |
| Idade do item mais antigo por fila | ≤ 300 s | alerta imediato por `search`, `index` ou `maintenance` |
| Falhas terminais por classe | ≤ 5,0% | janela móvel de 1 h; excluir cancelamentos da razão |
| Purge da referência | ≤ 900 s | zero referência vencida; alerta para qualquer atraso |
| Purge de candidatas | ≤ 86.400 s | zero candidata vencida; alerta para qualquer atraso |
| CPU por processo | `search` 75%, `index` 85%, `maintenance` 75% | acima do limite, pausar promoção e reduzir admissão/indexação |
| Memória por processo | `search` 460 MiB, `index` 690 MiB, `maintenance` 230 MiB | aproximadamente 90% dos limites Compose; alerta antes do OOM |

O ensaio de 100 consultas da task 6.3 SHALL produzir p50/p95, throughput, profundidade/idade da fila, falhas e recuperação após restart. A execução ARM da task 6.4 é o gate que confirma ou revisa estes números antes do canary de produção.

## Dimensões permitidas

Cada amostra ou alerta usa apenas `environment`, `type` e `state`, acompanhados de valores numéricos agregados. `type` identifica uma classe de worker (`search`, `index`, `maintenance`) ou um sinal técnico (`runtime`, `reference`, `candidate`). Logs e painéis não recebem identificadores de negócio nem payload facial.

O endpoint autenticado `GET /admin/facial-observability` entrega esse contrato em JSON. O parâmetro operacional opcional `expected_enabled` compara o kill switch efetivo com o estado esperado pelo deploy. As admissões aceitas e recusadas por backpressure são contadores agregados do processo da API; o coletor externo MUST somar réplicas e tratar restart como início de uma nova série. CPU e memória vêm do coletor de containers e entram no mesmo validador antes de alimentar alertas.

## Ciclo protegido de rollout

O primeiro deploy de produção SHALL usar `FACIAL_PROCESSING_ENABLED=false`. A flag é somente o kill switch técnico: ela não cria autorização. Cada transição usa `python -m app.facial.manage_rollout` e exige ação, ambiente, etapa, SHA integral, referências opacas de inventário/backup/conjunto de gates, allowlist de UUIDs públicos, UUID do administrador e confirmação exata vinculada à operação. O recibo guarda o digest e a contagem da allowlist, nunca seu conteúdo em logs.

| Etapa | Estado técnico | Critério de saída |
| --- | --- | --- |
| `dark` | rollout preparado, busca indisponível | migrations, modelos, chaves, portas, healthchecks e smoke sem PII aprovados |
| `canary` | menor allowlist aprovada | janela observada sem alerta crítico e validação de busca/retenção/purge |
| `limited` | expansão explicitamente aprovada | SLOs e capacidade sustentados; nenhuma regressão de segurança/privacidade |
| `general` | escopo geral aprovado | somente após aprovação humana de todos os gates e registro da promoção |

Promoção SHALL ocorrer uma etapa por vez. Suspensão exige a mesma etapa e allowlist explícitas, bloqueia novas admissões e agenda limpeza do escopo. O kill switch global é reservado para risco sistêmico; desligá-lo não substitui purge, investigação nem o recibo de suspensão.

## Resposta operacional

1. Suspender novas admissões no escopo afetado ou desligar o kill switch quando houver risco sistêmico.
2. Manter o consumidor `maintenance` ativo para retenção e purge sempre que for seguro.
3. Confirmar contagens agregadas de referências/candidatas vencidas e estado das três filas.
4. Não ampliar rollout enquanto qualquer alerta crítico estiver disparado.
5. Preservar fotos, seleções, pedidos, pagamentos e mídia histórica; somente derivados faciais do escopo revogado podem ser eliminados.

O procedimento completo de RIPD, responsabilidades, incidente, recuperação e comunicação está em `GOVERNANCA-E-INCIDENTE-BUSCA-FACIAL.md`.
