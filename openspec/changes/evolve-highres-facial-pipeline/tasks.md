## 1. Auditoria e baseline
- [x] 1.1 Rastrear upload, jobs, derivados, facial, ajuste, purge e frontend; registrar referências e divergências em audit.md.
- [x] 1.2 Executar regressões existentes focadas e registrar baseline verificável. Provider/engine/indexing/preview_adjustment: 39 passed, 3 avisos de depreciação preexistentes, 164,68 s no Windows Python 3.12.
- [ ] 1.3 Preparar corpus autorizado anotado e medir recall/recuperação atual separadamente; depende de caminho/origem/ground truth.

## 2. Lifecycle
- [x] 2.1 Adicionar schema aditivo de lifecycle/regiões/modelo/consulta e validar upgrade/downgrade em banco descartável.
- [x] 2.2 Integrar upload atômico limitado, admissão com quotas/reserva, job facial antes da mídia e retry; testar falhas e concorrência.
- [x] 2.3 Integrar remoção após artefatos, TTL/cleanup e regeneração sem fonte; testar não exclusão prematura, órfãos e flag.

## 3. Detecção e persistência
- [x] 3.1 Implementar planner global/multiscale/tiles, transformação e dedup; testar overlap/bordas/orientação/orçamento.
- [x] 3.2 Alinhar no high-res, persistir regiões/metadados/métricas e isolamento de modelo com abstração de embedding; testar idempotência e qualidade geométrica.
- [x] 3.3 Preservar métricas sanitizadas de tentativas malsucedidas e completar agregados administrativos por galeria; testar falha parcial, retry e isolamento. 39 testes focados aprovados em 15,39 s.

## 4. Busca
- [x] 4.1 Integrar API de regiões e consulta por UUID aos gates/fila/snapshot existentes; testar IDOR, revogação, selfie e ausência de redetecção.
- [x] 4.2 Separar classificação de similaridade e qualidade, expor faixa ambígua calibrável e manter restante; testar versões/modelos/galerias.

## 5. Apresentação
- [x] 5.1 Implementar overlays adaptativos/zoom/pan/viewport e ações externas; testar mobile, teclado, clique e seleção.
- [x] 5.2 Integrar prévias 1980/adaptativas e invariáveis Auto Adjustment; testar geometria e alteração fotométrica sem reindex.

## 6. Benchmark e gates
- [x] 6.1 Criar harness reproduzível de recall/duplicatas e retrieval/top-k/calibração/custos separados; validar com corpus sintético de contrato e benchmark NumPy.
- [x] 6.2 Documentar licenças/proveniência/dataset/pesos EdgeFace e decisão de produção com fontes primárias.
- [ ] 6.3 Medir before/after e calibrar detecção/query/match no corpus real; manter pendente até evidência.
- [ ] 6.4 Comparar SFace/EdgeFace sobre mesmas regiões se licença e runtime permitirem; não escolher vencedor sem evidência.
- [ ] 6.5 Medir ARM64 4 cores e impacto API/Postgres/Redis/Evolution/web/ajuste, escolher recursos com evidência; exige inventário e autorização remota.

## 7. Integração e entrega
- [x] 7.1 Executar regressões backend/frontend, lint, typecheck/build, OpenSpec e diff; corrigir falhas locais. Backend amplo: 637 passed, 3 skipped, nenhuma falha; complementares e limites em validation.md.
- [x] 7.2 Validar rollback da flag/coexistência, purge e fluxo ponta a ponta sintético; registrar limitações operacionais.
- [ ] 7.3 Validar fluxo real autenticado desktop/mobile, relatório de métricas e aceite humano; sem sync/archive automático.
- [ ] 7.4 Preparar publicação da versão local em PR para homologação com inventário e plano de impacto zero verificáveis.
- [ ] 7.5 Após CI e gates humanos, publicar mesma versão/schema/modelos em homologação, ativar high-res se explicitamente aprovado e verificar paridade/saúde/terceiros.

## Evidências e bloqueios

Ver validation.md para comandos, resultados e limites. 2.1–5.2, 6.1–6.2 e 7.2 possuem implementação e testes locais; 7.2 refere-se ao fluxo sintético integrado de serviços e rollback da admissão, não a um deploy.

- 1.3/6.3: bloqueadas por corpus/origem/anotação ausentes, apesar da autorização privada já recebida.
- 2.2: concluída após PostgreSQL 16 descartável local: quota entre processos, idempotência do mesmo ativo, SKIP LOCKED durante leitura e upgrade/downgrade/upgrade real. Ver test_highres_postgresql.py e validation.md.
- 6.4: depende de corpus e licença/autorização da variante dos pesos EdgeFace; nenhuma troca de modelo realizada.
- 6.5: depende de inventário/acesso e autorização remota específica; configurações ARM não escolhidas por intuição.
- 7.1: concluída localmente em 20/09/2026. Backend amplo 637 aprovados/3 skips opcionais PostgreSQL; integração 95 aprovados; diagnóstico/provider 39 aprovados e handler de upload 1 aprovado. PostgreSQL específico high-res: 4 aprovados. Frontend 296/297 na suíte, expectativa restante corrigida e arquivo completo com 10 aprovados. Build/typecheck/lints/OpenSpec/Compose/diff aprovados. Totais de suítes se sobrepõem; não somar como testes únicos.
- 7.3: exige lote real, sessão autenticada e aceite humano. Não sincronizar nem arquivar automaticamente.
- 7.4–7.5: adicionadas pelo pedido de paridade local/server de 20/09/2026. Inventário remoto e plano em deployment-inventory.md; nenhuma escrita remota nesta preparação. Aguardar conferência humana do CI após push, preservando preferência registrada.
