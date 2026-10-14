## Purpose

Estabelecer um gate verificável para avaliar busca facial privada por evento sem liberar biometria a clientes antes de segurança, privacidade e viabilidade técnica comprovadas.

## ADDED Requirements

### Requirement: Escopo restrito e dados seguros do spike

O spike SHALL usar somente imagens sintéticas ou devidamente anonimizadas, entre 500 e 1.000 JPEGs, e limitar toda busca a um único evento de teste, sem disponibilizar grade coletiva ou resultado a clientes reais. Imagens, referências, embeddings e índices do experimento SHALL NOT ser versionados no Git, enviados à homologação ou reaproveitados no produto.

#### Scenario: Tentativa com dado real

- **WHEN** o operador propõe executar o spike com dado biométrico real de criança ou produção
- **THEN** o procedimento é bloqueado e registra a necessidade de aprovação e base legal específica antes de qualquer continuidade

#### Scenario: Encerramento do experimento
- **WHEN** uma execução do benchmark termina ou falha
- **THEN** imagens de consulta, embeddings, índices e temporários são eliminados e somente métricas agregadas sem dado biométrico permanecem no relatório

### Requirement: Pipeline de indexação e filtro avaliado

O spike SHALL medir separadamente a indexação assíncrona de zero ou mais rostos por foto e a consulta posterior com exatamente um rosto utilizável. A consulta SHALL comparar somente o evento autorizado e retornar uma lista ordenada de fotos candidatas sem criar galeria privada, seleção, vínculo ou autorização.

#### Scenario: Consulta encontra candidatos
- **WHEN** a referência sintética possui um rosto utilizável e encontra correspondências no evento isolado
- **THEN** o harness retorna candidatos ordenados e comprova que nenhuma entidade comercial ou de acesso foi criada

#### Scenario: Referência inválida
- **WHEN** a referência contém nenhum rosto, vários rostos ou qualidade insuficiente
- **THEN** o harness devolve estado específico, não executa associação automática e elimina a referência e seu embedding

#### Scenario: Isolamento entre eventos
- **WHEN** um embedding semelhante existe fora do evento consultado
- **THEN** ele não participa da busca nem aparece nos resultados ou métricas daquela consulta

#### Scenario: Indexação falha
- **WHEN** o processamento facial de uma foto falha
- **THEN** o harness registra falha facial retomável sem tratar a prévia fotográfica como indisponível

### Requirement: Avaliação de privacidade e consentimento

O spike SHALL documentar separadamente a base legal e transparência necessárias para indexar os rostos do acervo e o consentimento específico da pessoa que envia a referência, além de finalidade, retenção, exclusão automática e manual, revogação, revisão humana condicional, tratamento de menores e auditoria necessários para uma futura busca facial privada.

#### Scenario: Resultado do desenho de privacidade

- **WHEN** a avaliação de privacidade é concluída
- **THEN** ela registra os controles mínimos e os riscos remanescentes antes de recomendar qualquer implementação de produto

### Requirement: Critérios técnicos de decisão

O spike SHALL verificar licença comercial do código e de cada peso, compatibilidade ARM, cobertura de detecção, precisão, falsos positivos/negativos, latência e throughput de indexação e consulta, uso de CPU, memória e disco, e emitir decisão explícita de aprovar, ajustar ou rejeitar a futura funcionalidade. Métricas SHALL identificar modelo, versão e limiar e SHALL favorecer a redução de falsos positivos.

#### Scenario: Critério reprovado

- **WHEN** um critério obrigatório de segurança, licença, precisão ou desempenho não for atendido
- **THEN** o spike recomenda não habilitar busca facial em galerias de clientes e registra a limitação

#### Scenario: Peso sem licença comercial comprovada
- **WHEN** o código possui licença permissiva, mas o peso pré-treinado não permite uso comercial verificável
- **THEN** o candidato é excluído da recomendação de produção independentemente de sua precisão
