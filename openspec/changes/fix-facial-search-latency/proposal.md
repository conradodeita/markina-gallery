## Why

Em 14/10/2026, o proprietário relatou busca por clique que demora minutos e termina em falha na primeira galeria real, com duas pastas e 2.691 fotos. Inspeção somente de leitura no servidor confirmou índice concluído (10.531 rostos em 2.687 fotos), consulta com snapshot 2.691/2.691, zero comparações concluídas, quatro tentativas e falha por timeout após 376,77 segundos. Logs registram lease expirado durante a comparação. O callback anterior recarrega e grava o snapshot inteiro antes de cada rosto; não renova o lease durante a comparação.

## What Changes

- Corrigir a consulta ao snapshot para verificar apenas a foto corrente, conservando autorização, versões e fingerprint congelado.
- Comparar embeddings em lotes limitados, renovar lease e publicar progresso real durante a comparação.
- Registrar regressões de volume, isolamento, revogação, prazo e memória, com evidências sintéticas locais.
- Preparar implantação limitada ao worker de busca, sujeita à autorização explícita e inventário operacional.

## Capabilities

### New Capabilities

- `privacy-biometric/bounded-facial-comparison`: comparação durável com custo e memória limitados sem relaxar privacidade.

### Modified Capabilities

- Nenhuma mudança de acesso, engine, limiar, consentimento ou seleção comercial.

## Impact

Worker e engine facial, testes e documentação. Base de implementação isolada no commit implantado `3b15529`; a árvore original contém trabalho preexistente e permanece preservada. Há dados reais em `markina.pickyourpic.com.br`, proprietário `conradodeita@gmail.com`, pagamento inicial PIX. Sem migration, reindexação, exclusão de acervo, alteração de segredo ou reset. Pedido atual autoriza diagnóstico/correção local; deploy continua sujeito a aprovação humana.
