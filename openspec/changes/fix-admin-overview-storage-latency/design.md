## Context

Diagnóstico em `docs/diagnostics/admin-overview-performance-2026-10-30.md`. `measure_owned_photo_storage` é a rotina do painel; o helper global de manutenção não pode substituí-la. O resumo bloqueia até concluir a medição e deve manter seu contrato atual. Base atual `origin/main=86c80806`, sem avanço remoto na consulta inicial; branch isolada `codex/fix-admin-overview-storage-latency`.

## Goals / Non-Goals

Reduzir custo frio e eliminar repetição da medição na navegação, preservando exatidão do snapshot e isolamento. Sem UI nova, worker, fila, migration, mudança de outros consumidores de paths, alterações financeiras ou cache compartilhado entre contas.

## Decisions

### Autorização por operação, com revalidação de saída

Validar tenant ativo antes de consultar cache/dados e novamente antes de devolver ou publicar qualquer resultado, inclusive cache hit e indisponibilidade. As três consultas de mídia continuam filtradas por tenant. O número de SELECTs de autorização não pode crescer com a quantidade de arquivos. Suspensão detectada no fim impede resposta e publicação no cache.

### Cache limitado ao fotógrafo e ao banco

LRU em memória com no máximo 128 entradas, chave formada pelo bind do banco, UUID do tenant e raízes resolvidas. TTL de 30s contado desde o início da coleta; cache somente de medição disponível/completa. Lock por entrada coalesce leituras simultâneas; nenhum lock global permanece durante SQL/IO. Limpar o cache existente também invalida entradas próprias. Reinício naturalmente invalida a memória. Contagem de fotos permanece atual em cada resposta; bytes representam snapshot de até 30s, não um ledger financeiro.

### Resolver os mesmos caminhos com menos trabalho

Consultar ID/chave de foto, caminho de derivado e chaves/item de mídia histórica, sem materializar entidades completas. Fixar as três raízes resolvidas no começo e verificar cada chave original e resolvida com o `media_namespace` existente. O candidato deve permanecer dentro de sua raiz específica; histórico deve conservar prefixo do item antes e depois da resolução. Usar `photo_files` existente para ajustes legados/atuais. Deduplicar por caminho físico resolvido. Arquivo ausente não conta; erro ou arquivo não regular torna a medição inteira indisponível, sem total parcial. Helpers de servir/processar mídia não serão alterados.

### Agregação SQL no resumo

Substituir materialização de MediaJob por GROUP BY status e listas de IDs por COUNT. Preservar todos os filtros atuais, sem misturar tenant ou lifecycle. Galerias recentes e o contrato de storage continuam iguais.

## Risks / Trade-offs

Bytes podem refletir até 30s anteriores; isolamento e acesso são revalidados mesmo em cache hit. Primeira coleta continua dependente do filesystem; nenhum prazo garantido de produção será prometido com base em benchmark local. Evicção durante uma coleta pode permitir coleta extra, sem misturar resultados. Mudança de raiz/banco gera outra chave; não reusar cache global de manutenção. Limites/symlinks precisam de testes antes de substituir a resolução repetida.

## Migration Plan

Implementação local e testes de fronteira/performance por contagem de queries; regressões do resumo e tenancy. Se necessário, comparar candidato em processo isolado READ ONLY com o mesmo acervo, sem substituir código do servidor. Publicar somente via release autorizado; rollback de imagem API é compatível, sem migration ou dados novos. Manter change ativa e registrar qualquer verificação de navegador pós-publicação pendente.
