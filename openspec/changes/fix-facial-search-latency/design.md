## Context

O runtime implantado revalida owner, lease, política, público e snapshot antes de descriptografar cada rosto. A callback executa duas leituras completas do snapshot e commit por rosto; 10.531 rostos multiplicam o trabalho das 2.691 fotos. A comparação também acumula registros ORM, tuplas e matriz completa. O worker tem 512 MiB e 0,75 CPU; não alterar esses limites por intuição.

## Goals / Non-Goals

Restaurar consulta pelo índice pronto com memória limitada e lease renovado; preservar contratos de `simplify-mobile-gallery-face-search`, `evolve-highres-facial-pipeline` e isolamento do piloto. Não mudar modelo/limiar, engine servido, permissões, retenção, schema ou dados existentes.

## Decisions

1. Antes da comparação, continuar a preparação integral do snapshot existente. Na callback por rosto, consultar apenas a foto corrente e seu item do snapshot, com mesmo owner/galeria/cliente, prévia pronta, público vigente e último job de índice compatível. Exigir igualdade com fingerprint congelado; índice alterado não entra silenciosamente.
2. Conservar revalidação de request, owner, origem, política e lease antes da descriptografia. Renovar o lease por progresso em intervalo inferior ao seu vencimento, contando fotos distintas realmente comparadas; não fabricar percentual por rostos quando o contrato conta fotos.
3. Ler o índice com paginação por chave estável (UUID da foto e ordinal), em lotes limitados; não depender de cursor aberto durante commits. Projetar somente os campos necessários sem materializar entidades ORM, descriptografar e comparar vetorialmente o rosto corrente e descartar seu vetor em seguida; manter no acumulador apenas a melhor candidata por foto, com ordenação e thresholds idênticos. Atualizar o contador de uma foto somente depois de comparar todos os seus rostos, inclusive quando eles atravessarem lotes.
4. Revalidar acesso e snapshot antes de publicar candidatas; recusa, cancelamento ou lease perdido impede publicação. Falhas sanitizadas preservam as retentativas e a jornada manual.
5. Testes usam envelopes e imagens sintéticos, incluindo escala de 2.691 fotos/10.531 rostos; nenhuma biometria real será exportada ou persistida em testes.
6. A medição local isolada com volume equivalente levou 57,42 segundos, ainda sem callback completo do worker. Condensar consultas redundantes ao mesmo owner/galeria/política em uma leitura SQL por rosto, com os mesmos predicados vigentes e sem cache entre descriptografias; conservar a consulta de público/lease e os gates de rollout/calibração. Cancelamento ou lease perdido retorna ao loop sem tentar falhar novamente um job que já não pertence ao consumidor.

## Migration Plan

Sem migration. Validar testes faciais/isolamento e lint local, revisar diff, apresentar inventário e plano ao proprietário. Após autorização, implantar somente o consumidor de busca via imagem derivada da versão vigente, preservar a imagem anterior para rollback e verificar saúde e busca autenticada na galeria existente. Não executar o deploy geral que pode acionar manutenção/limpeza.

## Risks / Trade-offs

Revalidação por rosto conserva custo linear de banco. Medir latência real após aprovação; testes sintéticos não comprovam precisão facial nem capacidade concorrente de produção. Paginação não admite fotos fora do snapshot; revogação no meio da consulta deve bloquear leitura/publicação.
