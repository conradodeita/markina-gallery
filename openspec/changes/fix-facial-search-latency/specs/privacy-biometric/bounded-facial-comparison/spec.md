## ADDED Requirements

### Requirement: Comparação limitada e durável do índice autorizado

O worker SHALL comparar somente embeddings compatíveis do snapshot congelado autorizado, com custo linear no número de rostos e memória limitada por lote. Resultados SHALL preservar deduplicação, bandas de qualidade, classificação e ordenação vigentes.

#### Scenario: Acervo com milhares de fotos
- **WHEN** uma consulta autorizada por região ou upload usa um snapshot pronto com 2.691 fotos e 10.531 rostos
- **THEN** o consumidor compara o índice em lotes limitados, renova o lease e conclui sem reexecutar a indexação nem redetectar a região escolhida

#### Scenario: Revogação durante a comparação
- **WHEN** owner, vínculo, política, origem, público ou lease perde validade antes de ler um embedding ou publicar o resultado
- **THEN** a operação impede esse efeito e não reutiliza autorização armazenada para contornar a recusa

#### Scenario: Índice ou público alterado
- **WHEN** uma foto sai do público autorizado ou seu fingerprint diverge do snapshot congelado
- **THEN** seu embedding não é descriptografado nem publicado nessa consulta, e fotos novas fora do snapshot não entram

#### Scenario: Vários rostos e progresso
- **WHEN** uma foto possui mais de um rosto no lote
- **THEN** todos os rostos elegíveis participam da comparação, somente a melhor candidata da foto permanece e a foto conta uma única vez no progresso

### Requirement: Revalidação e progresso da comparação

Antes de cada descriptografia o worker SHALL revalidar owner ativo, origem, política, público da foto e lease, sem carregar ou gravar o snapshot completo para cada rosto. A comparação MUST renovar o lease antes do vencimento e expor progresso contado em fotos distintas efetivamente comparadas.

#### Scenario: Consulta atravessa o prazo inicial do lease
- **WHEN** uma comparação autorizada dura mais que o lease originalmente reservado
- **THEN** renovações demonstráveis mantêm o claim válido e o progresso conta cada foto somente depois de comparar todos os seus rostos

#### Scenario: Consulta cancelada ou lease perdido
- **WHEN** o consumidor deixa de possuir o claim durante a comparação
- **THEN** impede nova descriptografia/publicação, libera somente o lease próprio quando ainda existir e permanece disponível para o próximo job
