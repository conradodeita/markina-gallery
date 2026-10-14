## 1. Contratos de cobertura

- [x] 1.1 Adicionar testes do gerador para tamanhos 10, 74 e 96 em fotos horizontal, vertical e quadrada, medindo a extensão da ocorrência textual e verificando cobertura proporcional em vez de pixels absolutos. Evidência: matriz de 27 casos mede o eixo correspondente nas três proporções, direções e coberturas; suíte focada aprovou 42 testes.
- [x] 1.2 Cobrir horizontal, vertical e diagonal, texto longo, posições extremas, fallback de fonte, ocorrência única, ausência de corte e grade de segurança inalterada. Evidência: contratos parametrizados verificam contenção da composição, fallback proporcional e composição única da grade/texto; suíte focada aprovada.

## 2. Escala proporcional no derivado

- [x] 2.1 Implementar cálculo de fonte pela cobertura-alvo do eixo correspondente e verificar por teste que `74` aproxima 74% quando há espaço suficiente. Evidência: `_watermark_font_size` mede o texto, usa largura/altura/diagonal útil e encontra por busca binária a maior fonte dentro da cobertura.
- [x] 2.2 Aplicar contenção uniforme após rotação com margem mínima, preservar âncora, cor, opacidade, sombra e composição única, e verificar os casos limite sem distorção. Evidência: caixa rotacionada é contida antes da composição e os testes confirmam âncoras inteiras em posições extremas; cor, opacidade, sombra e grade permanecem no fluxo existente.

## 3. Prova administrativa equivalente

- [x] 3.1 Atualizar rótulo e ajuda do campo para explicitar porcentagem de cobertura, mantendo entrada validada de 10 a 96, e verificar acessibilidade e payload inalterado no teste da página de configurações. Evidência: campo acessível `Cobertura da marca-d’água (%)`, ajuda contextual, limites 10–96 e payload `watermark_size: 74` aprovados.
- [x] 3.2 Fazer a prova medir texto, contêiner e direção para representar a mesma cobertura proporcional; verificar 10, 74 e 96, redimensionamento e as três direções em teste direcionado. Evidência: prova mede texto por Canvas com fallback, observa redimensionamento e aplica contenção equivalente; testes cobrem as três direções e crescimento responsivo.

## 4. Validação e entrega

- [x] 4.1 Executar testes de mídia e configurações direcionados, Ruff, ESLint dos arquivos alterados, typecheck e OpenSpec estrito; revisar o diff para confirmar ausência de migration, alteração da grade, reenfileiramento automático ou reindexação facial. Evidência: 42 testes de marca-d’água e 30 testes frontend focados aprovados; Ruff, typecheck, build, OpenSpec estrito e diff check aprovados; ESLint sem erros (avisos preexistentes de imagem/fixtures).
- [x] 4.2 Gerar amostras sintéticas nas três proporções e direções para inspeção visual, registrar a evidência e confirmar que nenhuma prévia existente foi reprocessada automaticamente. Evidência: matriz sintética 3×3 em 74% inspecionada em `C:\Users\Conrado\AppData\Local\Temp\markina-watermark-review\watermark-coverage-74-contact-sheet.jpg`; texto integral e proporcional nas nove combinações; geração isolada sem banco, fila ou acervo.
- [ ] 4.3 Preparar e apresentar inventário de impacto zero, executar o push, merge e deploy conjunto de backend/frontend em homologação já autorizados pelo usuário; depois validar novas prévias sem backfill do acervo. Evidência parcial: inventário apresentado, PR `#70` mergeado em `develop` no SHA `af2b0c00fb5762a4d43f8cddb233edd0b68c618b` e deploy `34665380268` aprovado em homologação; backend/frontend, saúde externa e pipeline completos aprovados. O deploy não executou backfill; permanece pendente validar uma prévia criada a partir de nova foto em homologação.
