## Context

Veja `proposal.md` para a motivação e o delta de `gallery-visualization-and-watermark-controls` para o contrato. A apresentação pública e privada da cliente reutiliza `GalleryPresentation` e a classe `.gallery-presentation-grid`, mas regras tardias em `globals.css` voltam a grade para uma coluna abaixo de 560 px. A proteção textual é incorporada ao `client_preview` pelo pipeline Pillow; hoje a camada de texto é posicionada por dois laços que a repetem pela imagem, enquanto a grade diagonal de segurança é desenhada separadamente.

## Goals / Non-Goals

**Goals:**

- Corrigir a causa compartilhada da coluna única sem duplicar regras por rota pública ou privada.
- Garantir duas células por linha inclusive em 320 px, com cada foto ocupando uma célula no mobile.
- Transformar somente a camada textual em uma ocorrência única, preservando direção, posição, tamanho, cor, opacidade, tipografia e sombra.
- Preservar a grade de segurança e o pipeline existente de derivados protegidos.

**Non-Goals:**

- Alterar grids administrativos, autorização, seleção, reconhecimento facial ou contratos de API.
- Criar novos controles de marca-d’água ou modificar a aparência/periodicidade da grade de segurança.
- Reenquadrar, recortar ou converter fotos para uma proporção única.

## Decisions

### 1. Corrigir a cascata final da grade compartilhada

A regra canônica da grade fotográfica da cliente terá duas colunas no mobile, três em tablet e quatro ou mais quando a largura comportar. Overrides finais que agrupam `.gallery-presentation-grid` com diretórios/cards de outra natureza não poderão reduzi-la a uma coluna. No breakpoint mobile, `grid-column` de cada foto será limitado a uma célula para que imagens horizontais não ocupem a linha inteira.

Isso mantém um único contrato para a Galeria pública, a privada e os grupos de resultados faciais, pois todos usam o mesmo componente. A alternativa de corrigir cada página foi descartada por recriar divergências e permitir regressão pela ordem da cascata.

### 2. Preservar proporção dentro de células estreitas

As células continuam calculando sua proporção a partir dos metadados conhecidos e a imagem permanece com `object-fit: contain`. Gutter lateral e gap serão compactos no mobile, sem rolagem horizontal; controles de seleção e foco manterão área acionável adequada.

A alternativa de `object-fit: cover` foi descartada porque recortaria conteúdo fotográfico e poderia ocultar pessoas nas prévias.

### 3. Compor a camada textual uma única vez

O pipeline continuará criando uma camada RGBA para o texto, aplicando a rotação correspondente e calculando a âncora configurada. Em vez de percorrer linhas e colunas para mosaico, fará uma única composição, com coordenadas limitadas à área visível quando o texto rotacionado se aproximar das bordas. O desenho repetido da grade de segurança permanece em seu bloco independente e não será alterado.

A alternativa de ocultar cópias via CSS foi descartada porque a marca está gravada no JPEG protegido, não sobreposta pelo navegador.

### 4. Não reenfileirar as fotos existentes automaticamente

Não haverá migration de banco nem job de backfill. Novos `client_preview` usarão o novo algoritmo, enquanto as prévias já existentes permanecerão inalteradas, conforme decisão do proprietário de que o acervo atual é somente de teste. O fluxo administrativo vigente continuará podendo reprocessar no futuro apenas quando o fotógrafo salvar deliberadamente uma configuração de proteção.

Uma reindexação facial não é necessária, pois o reconhecimento usa a prévia administrativa limpa e não o `client_preview` com marca-d’água.

## Risks / Trade-offs

- [Cards muito estreitos em aparelhos pequenos] → validar 320, 360 e 390 px, usar gaps compactos e impedir conteúdo interno de impor largura mínima.
- [Regra CSS posterior restaurar uma coluna] → adicionar teste estrutural sobre a última regra efetiva e teste de componente para o seletor compartilhado.
- [Texto rotacionado extrapolar a imagem] → limitar a âncora após a rotação e testar as três direções, posições extremas e tamanhos mínimo/máximo.
- [Fotos existentes conservarem o mosaico] → comportamento aceito explicitamente para o acervo atual de teste; não disparar backfill ou reenfileiração durante o deploy.
- [Mudança acidental da grade de proteção] → manter seu bloco de desenho intacto e comparar saída com grade habilitada em teste de regressão.

## Migration Plan

1. Publicar frontend e backend juntos após testes focados e build.
2. Confirmar duas colunas em galeria autenticada nos viewports mobile de referência.
3. Não salvar novamente a proteção nem reenfileirar o acervo existente durante o deploy.
4. Conferir novas prévias geradas depois da publicação em uma direção e tamanho representativos; as demais combinações ficam cobertas por testes automatizados.
5. Em rollback, retornar o código anterior; não há schema, dado ou fila de backfill a reverter. Derivados já gerados com texto único permanecem válidos.
