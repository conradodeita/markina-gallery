## Context

Observação da página autenticada pelo proprietário: o painel ocupa a largura inteira; worker, faces, jobs e escolha global aparecem em uma lista empilhada sem hierarquia. O botão fica separado do motor selecionado.

## Decisions

O painel SHALL usar os tokens existentes de superfície, borda, texto e foco. Um cabeçalho agrupa título e selo de homologação. Uma faixa interna apresenta o motor selecionado e o único botão de alternância. Em telas pequenas essa faixa empilha, com botão de largura total e altura mínima de 44 px.

O texto principal SHALL explicar o alcance global e o fallback por galeria. Um elemento nativo details/summary, recolhido inicialmente, SHALL conter os três indicadores agregados e o aviso de limiar não calibrado. Indicadores SHALL usar uma grade de três colunas no desktop e uma no celular. Abrir os detalhes SHALL NOT realizar requisição ou alterar a configuração.

O PATCH, os gates, a recusa de ativação sem worker pronto, a possibilidade de retorno a SFace e as mensagens de salvamento SHALL permanecer no contrato existente. Não há leitura de fotos, seleção de motor ou execução de benchmark durante a avaliação visual.

## Validation

Revisão do diff e validação OpenSpec, TypeScript e ESLint focados; prévia local usando fixtures agregadas sintéticas no navegador, em largura desktop e celular, sem API operacional. A inspeção da homologação é somente visual e não aciona o botão de troca.
