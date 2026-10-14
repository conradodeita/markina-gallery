## Context

Veja `proposal.md`, a delta spec e as changes anteriores de texto único e prova acima de 32. O gerador atual passa `watermark_size` diretamente como tamanho em pixels para a fonte. Em uma prévia de 1.600 × 1.067, 74 px representa menos de 7% da altura; ao redimensionar a imagem no navegador, a marca parece ainda menor. O intervalo persistido 10–96 já está validado e pode ser mantido sem migration, mas sua semântica precisa corresponder à cobertura visual esperada.

## Goals / Non-Goals

**Goals:**

- produzir cobertura visual comparável em diferentes resoluções e proporções;
- fazer `74` ocupar aproximadamente 74% do eixo útil escolhido;
- impedir corte após rotação e manter texto único e grade independentes;
- alinhar a prova frontend ao cálculo do derivado.

**Non-Goals:**

- repetir o texto, alterar a grade de segurança ou fornecer desenho livre;
- reprocessar automaticamente o acervo existente durante implementação ou deploy;
- mudar o intervalo persistido, criar coluna nova ou alterar o reconhecimento facial.

## Decisions

### O valor 10–96 passa a representar cobertura percentual

O valor persistido será dividido por 100 para obter a cobertura-alvo. Na direção horizontal, o comprimento natural do texto buscará essa fração da largura útil; na vertical, da altura útil; na diagonal, da diagonal útil. Essa semântica corresponde ao resultado que o fotógrafo deseja controlar e independe da resolução do derivado.

Alternativa descartada: apenas elevar o máximo de pixels. Um teto absoluto volta a produzir marcas diferentes entre fotos pequenas e grandes e não garante que `74` preencha a composição.

### A fonte é resolvida por medição, com contenção da camada rotacionada

O gerador medirá o texto na tipografia escolhida e encontrará o maior tamanho de fonte que aproxima a extensão-alvo. Depois da rotação, validará largura e altura contra uma caixa interna com margem; se exceder, reduzirá uniformemente até caber. A composição continuará ocorrendo uma única vez na âncora configurada.

Alternativa descartada: esticar a camada pronta até a largura desejada. Isso distorce glifos e pode produzir artefatos diferentes entre direções.

### A direção define o eixo de cobertura, não uma nova configuração

Horizontal usa largura, vertical usa altura e diagonal usa a diagonal geométrica. O mesmo campo e a mesma API permanecem; nomes e ajuda da interface deixam claro que o número é percentual de cobertura. Valores existentes continuam válidos e passam à nova interpretação apenas quando um derivado for gerado novamente.

Alternativa descartada: três tamanhos independentes. Isso aumenta complexidade sem necessidade e diverge das três direções já exclusivas.

### A prova mede seu próprio contêiner com a mesma regra

A prova administrativa calculará o tamanho a partir das dimensões renderizadas, do texto, da fonte e da direção, reproduzindo cobertura e contenção. Não usará o número como `font-size` absoluto. Redimensionamento da viewport recalcula somente a prova.

Alternativa descartada: multiplicador CSS fixo. Ele não considera comprimento do texto, proporção do contêiner nem rotação.

## Risks / Trade-offs

- [Textos muito longos exigirem fonte menor] → priorizar texto integral e informar na ajuda que a cobertura é aproximada com contenção.
- [Diferença entre métricas da fonte no navegador e no servidor] → validar tolerância visual e dimensões normalizadas, sem prometer igualdade de pixel.
- [Diagonal grande tocar bordas] → medir a caixa após rotação e respeitar padding mínimo antes da composição.
- [Configuração antiga gerar aparência muito maior em futura regeneração] → registrar a mudança sem backfill e mostrar a nova semântica na prova antes de salvar.
- [Fallback de fonte alterar medida] → usar a mesma família substituta prevista e testar o caminho de fallback.

## Migration Plan

1. Adicionar testes de mídia para 10, 74 e 96 em imagens horizontal, vertical e quadrada, com as três direções.
2. Implementar a medição proporcional e a contenção sem alterar o bloco da grade de segurança.
3. Atualizar rótulo/ajuda e prova administrativa com o mesmo conceito de cobertura.
4. Validar que nenhuma foto existente é reenfileirada automaticamente pela change ou pelo deploy.
5. Publicar frontend e backend juntos após autorização; rollback restaura o algoritmo anterior sem downgrade de banco. Derivados já gerados permanecem arquivos válidos.
