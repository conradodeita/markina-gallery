# Delta para deployment-operations

## ADDED Requirements

### Requirement: Modo cooperativo de manutenção

O backend SHALL oferecer um modo de manutenção opt-in, coordenado pelo Redis existente, sem migration e desativado por padrão. O gate MUST fechar novas admissões HTTP incompatíveis e novos ciclos dos workers compatíveis, preservando healthchecks, sessões e filas persistentes. Operações já admitidas MUST permanecer registradas até conclusão e ACK reais. A flag MUST permanecer habilitada em todos os processos participantes enquanto o gate existir.

#### Scenario: Manutenção desativada
- **WHEN** não há gate operacional ativo
- **THEN** ingressos HTTP e workers mantêm o comportamento normal, sem exigir configuração nova

#### Scenario: Novos ingressos durante manutenção
- **WHEN** um pedido HTTP incompatível com manutenção chega após o gate ser ativado
- **THEN** o backend responde 503 com `Retry-After` e `Cache-Control: no-store` antes de executar handler ou efeito, enquanto healthchecks permanecem acessíveis

#### Scenario: Upload ou requisição longa já admitida
- **WHEN** um upload ou pedido HTTP começou antes do gate
- **THEN** seu registro ativo permanece até a resposta terminar; a drenagem não aprova enquanto ele não confirmar conclusão

#### Scenario: Worker com trabalho ativo
- **WHEN** um worker compatível já iniciou um ciclo antes do gate
- **THEN** ele conclui o ciclo normalmente e confirma ACK somente após o processamento persistente; ciclos seguintes não reivindicam novas tarefas durante a manutenção

#### Scenario: Falha antes da confirmação
- **WHEN** um processo falha, Redis fica indisponível ou o ACK não pode ser persistido
- **THEN** a operação permanece registrada sem expiração automática, o gate não pode ser removido por timeout e a recuperação exige reconciliação explícita

#### Scenario: Requisição termina em erro de servidor
- **WHEN** uma requisição admitida retorna HTTP 5xx
- **THEN** seu recibo permanece sem ACK e a drenagem exige reconciliação, pois o efeito pode ser parcial

#### Scenario: Controle desativado ou Redis indisponível
- **WHEN** a flag `CONTROLLED_MAINTENANCE_ENABLED` está ausente/desativada, ou Redis falha enquanto a flag está ativa
- **THEN** o modo ausente preserva o comportamento normal sem consultar Redis, e o modo ativo recusa novas operações sem afirmar drenagem

#### Scenario: Tarefas pendentes e retomada
- **WHEN** o modo é encerrado por operação explícita após reconciliação
- **THEN** tarefas ainda pendentes permanecem na fila persistente e ingressos e workers retomam o comportamento normal

### Requirement: Callbacks financeiros e de mensagens durante manutenção

Retornos de pagamento e webhooks de mensagem SHALL ser tratados como operações críticas rastreadas, sem sucesso artificial. Um release MUST comprovar continuidade durante eventual parada/substituição da API antes de prosseguir.

#### Scenario: Callback aceito e persistido
- **WHEN** um callback crítico válido é recebido enquanto a API está ativa
- **THEN** ele passa pelo handler existente e seu registro ativo só recebe ACK depois do resultado normal e da persistência exigida por esse handler

#### Scenario: Callback falha
- **WHEN** a validação ou persistência de um callback falha
- **THEN** não é produzido sucesso artificial; falha sem ACK mantém a drenagem bloqueada até reconciliação

#### Scenario: Substituição da API sem continuidade comprovada
- **WHEN** um release requer parar ou substituir a API e não existe receiver durável nem retry/reconciliação comprovado para uma lacuna de callback
- **THEN** o gate de release permanece bloqueado, mesmo que os workers e ingressos comuns estejam drenados

#### Scenario: Gate sem cobertura
- **WHEN** o gate fecha novas admissões comuns
- **THEN** ele protege os caminhos presentes na revisão atual e não afirma controlar containers legados ou serviços que não carregaram a flag e a barreira

### Requirement: Bootstrap da manutenção em containers legados

O procedimento de release SHALL verificar se cada processo ativo reconhece o gate antes de depender dele. A manutenção MUST NOT considerar um gate Redis recém-ativado como controle retroativo sobre processos legados. A primeira transição SHALL permanecer bloqueada até que exista um protocolo de quiescência reconhecido pelos processos ativos ou uma estratégia supervisionada que comprove a prevenção de novos claims, o tratamento de operações em andamento, os efeitos externos e a recuperação.

#### Scenario: Processo legado não reconhece gate
- **WHEN** qualquer processo ativo não consulta cooperativamente o controle de manutenção
- **THEN** o executor recusa iniciar a primeira transição e identifica o risco residual para decisão operacional explícita

#### Scenario: Processo reconhece gate e confirma estado
- **WHEN** todos os processos ativos são compatíveis, a drenagem retorna sucesso e os estados persistentes não indicam trabalho ativo
- **THEN** o executor pode prosseguir somente conforme autorização e demais gates do release
