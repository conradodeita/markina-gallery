# Spec Delta

## MODIFIED Requirements

### Requirement: Monitor operacional com qualidade explícita
O sistema SHALL apresentar monitor com HTTP, pool, banco, filas, workers, armazenamento, host e incidentes, preservando o card existente. Toda métrica SHALL distinguir origem, instante, escopo e indisponibilidade; dados antigos MUST NOT indicar saúde atual.

#### Scenario: Fonte ausente
- **WHEN** o host não possui fonte configurada ou permitida
- **THEN** o painel mostra a lacuna, preserva as demais fontes e não inventa valores

#### Scenario: Consultas iniciais concorrentes da interface
- **WHEN** métricas, incidentes e árvore são solicitados pela mesma interface
- **THEN** a interface SHALL coordenar essas consultas sem exceder o limite de leituras do backend, preservar cancelamento e permitir progresso após falha, sem retentativas em loop

#### Scenario: Apresentação humana com dados técnicos preservados
- **WHEN** o proprietário abre o Monitor
- **THEN** vê Estado geral, Filas/uploads/processamento, Servidor/armazenamento, Fotógrafos/clientes, Incidentes/alertas e Capacidade/filas conforme suas permissões, sem as seções técnicas Aplicação e experiência e Qualidade da coleta na tela principal; os dados técnicos continuam disponíveis na coleta/exportação

#### Scenario: Dicas acessíveis de interpretação
- **WHEN** o proprietário solicita ajuda em um dos seis blocos
- **THEN** uma dica curta explica significado, limites e como acompanhar o indicador por teclado ou toque, sem depender de hover ou substituir dado ausente por zero

#### Scenario: Exportação identificada corretamente
- **WHEN** o proprietário escolhe baixar um relatório técnico JSON ou texto
- **THEN** recebe o contrato sanitizado existente com fontes, versão, qualidade, histórico, operações e incidentes autorizados, mesmo com detalhes retirados da UI, sem árvore ou dados pessoais
