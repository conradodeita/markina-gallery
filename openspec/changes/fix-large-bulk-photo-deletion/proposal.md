## Why

A exclusão em massa administrativa falha integralmente quando a seleção possui mais de 500 fotos, pois a interface envia todos os identificadores em uma única requisição enquanto a API limita cada lote a 500. O defeito foi observado em homologação com 637 fotos; operacionalmente, o sistema precisa excluir seleções superiores a 2.000 fotos sem exigir manipulação manual do lote.

## What Changes

- Fazer a interface dividir seleções grandes em lotes aceitos pela API, preservando uma única confirmação humana para a operação completa.
- Manter a proteção comercial aplicada individualmente pelo backend e consolidar os totais de fotos removidas, bloqueadas e ausentes entre todos os lotes.
- Diante de falha intermediária, informar a remoção parcial já confirmada e atualizar a pasta para que uma nova tentativa seja segura.
- Cobrir por teste uma seleção superior a 2.000 fotos, sem ampliar nem remover o limite defensivo do backend.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-visualization-and-watermark-controls`: explicitar que uma seleção administrativa maior que o limite de transporte SHALL continuar sendo uma única operação confirmada para o fotógrafo, executada em lotes seguros e com resultado consolidado.

## Impact

- Frontend administrativo da etapa Imagens da Galeria pública.
- Contrato já existente `DELETE /admin/photo-folders/{folder_id}/photos`, sem alteração incompatível na API.
- Testes de interface para particionamento, consolidação e falha parcial.
- Nenhuma migration, dependência, mudança de segredo ou ação direta sobre dados de homologação.
