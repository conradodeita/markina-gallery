## Why
O administrador consegue remover galerias e fotos, mas a interface esconde a exclusão de pastas com conteúdo e a API rejeita pastas liberadas. A solicitação humana autoriza implementar essa operação nas pastas públicas e nas pastas próprias de galerias privadas.

## What Changes
- Permitir excluir uma pasta de conteúdo e suas fotos após confirmação explícita com nome, quantidade e impacto nos vínculos.
- Aplicar a política comercial existente a todas as fotos antes da remoção transacional; pagamento em análise bloqueia a pasta inteira, compras confirmadas preservam histórico e mídia histórica.
- Reutilizar limpeza de fotos, arquivos e registros biométricos, com auditoria e isolamento do escopo.

## Capabilities
### Modified Capabilities
- `media-storage/staged-folder-release`: exclusão administrativa de pastas com conteúdo, inclusive liberadas.

## Impact
API administrativa e interfaces de galerias públicas e privadas; testes de regressão. Sem migration, mudança de configuração ou exclusão operacional de dados reais. Publicação permanece sujeita ao fluxo de revisão e deploy existente.

## Non-goals
Não alterar política comercial, retenção histórica, exclusão de galeria, permissões de cliente ou publicação de fotos.
