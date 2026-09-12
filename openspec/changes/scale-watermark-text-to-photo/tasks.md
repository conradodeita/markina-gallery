## 1. Contratos de cobertura

- [ ] 1.1 Adicionar testes do gerador para tamanhos 10, 74 e 96 em fotos horizontal, vertical e quadrada, medindo a extensão da ocorrência textual e verificando cobertura proporcional em vez de pixels absolutos.
- [ ] 1.2 Cobrir horizontal, vertical e diagonal, texto longo, posições extremas, fallback de fonte, ocorrência única, ausência de corte e grade de segurança inalterada.

## 2. Escala proporcional no derivado

- [ ] 2.1 Implementar cálculo de fonte pela cobertura-alvo do eixo correspondente e verificar por teste que `74` aproxima 74% quando há espaço suficiente.
- [ ] 2.2 Aplicar contenção uniforme após rotação com margem mínima, preservar âncora, cor, opacidade, sombra e composição única, e verificar os casos limite sem distorção.

## 3. Prova administrativa equivalente

- [ ] 3.1 Atualizar rótulo e ajuda do campo para explicitar porcentagem de cobertura, mantendo entrada validada de 10 a 96, e verificar acessibilidade e payload inalterado no teste da página de configurações.
- [ ] 3.2 Fazer a prova medir texto, contêiner e direção para representar a mesma cobertura proporcional; verificar 10, 74 e 96, redimensionamento e as três direções em teste direcionado.

## 4. Validação e entrega

- [ ] 4.1 Executar testes de mídia e configurações direcionados, Ruff, ESLint dos arquivos alterados, typecheck e OpenSpec estrito; revisar o diff para confirmar ausência de migration, alteração da grade, reenfileiramento automático ou reindexação facial.
- [ ] 4.2 Gerar amostras sintéticas nas três proporções e direções para inspeção visual, registrar a evidência e confirmar que nenhuma prévia existente foi reprocessada automaticamente.
- [ ] 4.3 Preparar inventário de impacto zero e solicitar autorização humana específica antes de push, merge ou deploy conjunto de backend/frontend em homologação; depois validar novas prévias sem backfill do acervo.
