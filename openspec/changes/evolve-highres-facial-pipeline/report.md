# Relatório da evolução facial — implementação local

## Situação

A implementação local está disponível sob `FACIAL_HIGHRES_ENABLED=false` por padrão. A iniciativa **não está homologada nem concluída nos critérios reais de aceitação**: faltam corpus anotado, calibração, avaliação ARM e fluxo autenticado com fotos reais. Não houve deploy. Resultados executados e comandos estão em [validation.md](validation.md); estado acionável em [tasks.md](tasks.md).

## O que mudou e por quê

O fluxo existente produzia derivados antes de analisar `admin_preview`; o detector limitava novamente a imagem e extraía embeddings nesse espaço reduzido. Havia criptografia, consulta por referência, filas, purge, isolamento e ajuste de prévia funcionais, preservados nesta implementação. A auditoria também encontrou divergência entre dimensões do detector e da avaliação de qualidade. Ver [audit.md](audit.md).

Fotos novas aderentes passam a ter uma fonte JPEG temporária com reserva durável, quotas e backpressure. A análise orientada pelo EXIF precede os derivados: global, aprofundamento seletivo, tiles com overlap, restauração de coordenadas, NMS e alinhamento na fonte. Regiões normalizadas e embeddings cifrados ficam duráveis. O ajuste fotométrico existente continua usando sua fila, com invariável geométrica. A fonte só é removida após validação dos artefatos ou expiração explícita; falhas preservam retry até o TTL. Após descarte, não há fallback de detector no preview.

A galeria passou a oferecer clique em uma região persistida, reaproveitando fila, consentimento e isolamento da busca. A interface distingue correspondências, possíveis correspondências e outras fotos. Overlays são adaptativos, com zoom/pan; a seleção comercial ampliada fica fora da fotografia. Miniaturas usam ação menor e centralizada na base. Diagnósticos administrativos incluem lifecycle, contagens, duração, tentativas e agregados por galeria sem biometria bruta.

## Métricas disponíveis

| Medida | Legado | High-res | Interpretação |
|---|---:|---:|---|
| Recall real de detecção | Não medido | Não medido | Corpus e ground truth ausentes |
| Retrieval/top-k/FP/FN reais | Não medidos | Não medidos | Não inferir a partir de fotos sem embedding |
| Tempo do smoke, 3 JPEGs cinza | 2,407 s | 16,425 s | Sem rostos; verifica execução/custo do aprofundamento vazio |
| CPU do processo no smoke | 2,203 s | 15,094 s | Windows x64, uma thread OpenCV |
| Pico RSS amostrado | 422 MB | 540 MB | Processos novos, testes concorrentes; inadequado para tuning |
| Throughput do smoke | 74,78 fotos/min | 10,96 fotos/min | Não representa um evento nem valida ARM |

Relatório agregado: [synthetic-smoke.json](synthetic-smoke.json). NumPy 8000×128 usou 4.096.000 bytes; p50 de 0,723 ms e p95 de 3,143 ms, excluindo banco e descriptografia. Não há evidência para introduzir banco vetorial nesta fase.

## Modelos, configuração e riscos

SFace permanece no runtime. A/B com EdgeFace não foi executado, não há vencedor. Código oficial e pesos têm licenças distintas; os pesos EdgeFace-Base consultados são CC-BY-NC-SA-4.0 e não foram incluídos no produto. Outras variantes exigem análise própria. Fontes, proveniência e bloqueios estão em [edgeface-assessment.md](edgeface-assessment.md).

Os parâmetros de detecção, quotas e TTL são hipóteses de homologação, listadas em [benchmark-plan.md](benchmark-plan.md). Nenhum threshold foi anunciado como calibrado. A faixa ambígua fica desabilitada até configuração própria. Limites de CPU/RAM de produção não foram aumentados. Riscos ainda abertos: custo e recall em grupos reais, parâmetros de query/match, saturação dos orçamentos, responsividade dos serviços compartilhados e operação sob falha do host. Fonte expirada antes da conclusão exige reupload.

## Aceitação verificável

Regressão ampla backend: **637 aprovados, 3 skips opcionais PostgreSQL, zero falhas**, em 1h03m44s. Complementares: integração 95 aprovados; diagnóstico/provider 39; recuperação do handler de upload 1; concorrência/migrations high-res em PostgreSQL 4. Os grupos se sobrepõem. Frontend: 296/297 na execução ampla; a expectativa textual restante foi corrigida e os 10 testes do arquivo passaram. TypeScript, build Next.js, ESLint, Ruff, OpenSpec estrito, Compose e revisão do diff aprovados. Detalhes, datas e limitações em [validation.md](validation.md).

| Critérios do pedido | Evidência ou pendência |
|---|---|
| 1, 3–5: fonte real, dedup, geometria e não reescaneamento | Testes de provider/lifecycle/EXIF/multiscale, isolamento e viewport sintético |
| 2, 19, 24: ganho de recall, thresholds e comparação real | Bloqueados pelo corpus autorizado anotado |
| 6–10: descarte, retry, órfãos e Auto Adjustment | Integração sintética e testes de artefatos, TTL e geometria |
| 11–14, 18: selfie, clique, isolamento e classificação | Testes de engine/search/worker/regiões; modelo incompatível rejeitado |
| 15–17: UX, seleção ampliada e miniaturas | Testes frontend e navegador desktop/mobile com figuras sintéticas; E2E autenticado real pendente |
| 20–21: ARM e serviços responsivos | Dependem de inventário, acesso e autorização remota específica |
| 22–23: migration e rollback | Upgrade/downgrade/upgrade descartável SQLite/PostgreSQL; flag e coexistência testadas |
| 25: documentação | Proposal, design, deltas, tarefas, auditoria, benchmarks e validações nesta change |

Rollback validado significa interromper novas admissões pela flag e preservar leitura/lifecycle das fotos aderentes. Não significa recuperar pixels já apagados nem voltar indiscriminadamente ao binário anterior. Migration operacional, rollout, sincronização de specs e arquivamento continuam sujeitos aos gates do projeto.

## Próxima evidência necessária

O proprietário já autorizou homologação privada; falta localizar o lote e documentar origem/finalidade específicas. Sugestão: `C:\Users\Conrado\Pictures\Markina-benchmark`, fora do Git, começando com 30–50 JPEGs pós-edição representativos, referências de busca e anotações revisadas. O harness aceita manifesto privado com separação calibração/validação. Fotos arbitrárias da máquina não foram coletadas. Depois do baseline e da calibração, executar A/B permitido e medir ARM com plano de impacto zero; por fim validar o fluxo real autenticado e obter aceite humano.
