## Why

O prazo de seleção herdado da Galeria pública não está apresentado de forma confiável na jornada ativa da cliente, dificultando saber até quando fotos selecionadas ainda podem ser alteradas e enviadas ao checkout. A prévia administrativa da marca-d’água também reduz visualmente qualquer tamanho acima de 32 px, embora o contrato e o backend aceitem até 96 px, levando o fotógrafo a acreditar que a configuração não funciona.

## What Changes

- Garantir que a galeria privada use o prazo autoritativo derivado da configuração da Galeria pública, sem conceder prazo local independente.
- Exibir a data de encerramento à cliente quando houver fotos selecionadas ainda editáveis e nenhum pagamento tiver sido comunicado para esse conjunto.
- Ao expirar, bloquear seleção e finalização novas, preservando a consulta de pedidos e fotos já compradas conforme o contrato existente.
- Fazer a prova administrativa representar todo o intervalo suportado de tamanho da marca-d’água, de 10 a 96 px, sem o teto visual artificial de 32 px.
- Cobrir os dois comportamentos com testes direcionados, sem migration, reprocessamento de mídia ou alteração de arquivos já gerados.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `client-access/derived-galleries`: explicitar a herança autoritativa do prazo e sua apresentação durante uma seleção editável ainda sem pagamento comunicado.
- `gallery-visualization-and-watermark-controls`: exigir que a prévia administrativa represente fielmente todo o intervalo de tamanho aceito pelo servidor.

## Impact

- Contratos e projeções backend da galeria privada e da biblioteca da cliente.
- Rotas Next.js da galeria/biblioteca da cliente e painel administrativo de proteção visual.
- Testes backend e frontend direcionados aos estados de prazo, seleção, comunicação de pagamento e prévia da marca-d’água.
- Sem nova dependência, migration, mudança de segredos, processamento facial, integração externa ou reprocessamento retroativo de mídia.
