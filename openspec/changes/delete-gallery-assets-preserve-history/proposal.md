## Why

A exclusão da Galeria 01 em homologação falhou em `removing_records`, mantendo a origem em `deleting`. Além da falha técnica, a política anterior mantém acervo privado e mídia histórica, bloqueia pagamentos comunicados e cancela pendências, contrariando a decisão de produto aprovada pelo proprietário: excluir o acervo preservando os movimentos e estados comerciais por referências textuais.

## What Changes

- **BREAKING** Exclusão da galeria pública remove também galerias privadas dependentes, pastas, fotos, prévias e mídia histórica correspondente. Exclusão privada remove arquivos próprios e somente vínculos de fotos compartilhadas; outros acervos permanecem intactos.
- Preservar nomes das fotos, contexto da galeria/pasta, seleção não comprada, pedidos, valores, PIX congelado, comunicações e decisões, sem cancelar ou confirmar pagamentos por exclusão.
- Exibir referências sem imagens em Vendas e pagamentos e no histórico autorizado da cliente; impedir pagamento de novo conteúdo indisponível.
- Usar a mesma preparação de histórico nas exclusões de galeria, pasta e foto, com retomada durável de limpeza e compatibilidade explícita para operações antigas falhas.
- Substituir as decisões conflitantes de `improve-gallery-and-client-data-lifecycle` e `allow-gallery-folder-deletion` relativas à preservação do acervo e à política comercial de exclusão; preservar desvinculação de cliente e regras de acesso fora desse escopo.

## Capabilities

### New Capabilities
- `gallery-sales/asset-independent-history`: histórico textual de movimentos e pedidos após exclusão do acervo.

### Modified Capabilities
- `gallery-sales/operational-gallery-interface`: exclusão integral com histórico independente.
- `media-storage/staged-folder-release`: exclusão de pastas liberadas e suas fotos sem bloqueio financeiro.

## Impact

Backend, migration aditiva, worker de exclusão, projeções financeiras e interfaces administrativas/cliente. Testes PostgreSQL/SQLite e frontend. Nenhuma limpeza retroativa automática de galerias já excluídas; recuperação da operação real e publicação exigem os controles operacionais do projeto. O proprietário aprovou o comportamento e pediu sua implementação explicitamente com “Aplique essa change”.
