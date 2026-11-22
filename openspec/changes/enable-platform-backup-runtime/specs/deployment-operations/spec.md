## ADDED Requirements

### Requirement: Baseline da publicação API/web comprovada
O manifesto de release SHALL identificar o SHA exato da última publicação API/web confirmada e saudável. O baseline SHALL avançar somente após o release protegido concluir com sucesso e as evidências pós-release confirmarem os serviços publicados. CI verde, preflight ou release falho/ignorado MUST NOT avançar o baseline.

#### Scenario: Publicação API/web confirmada
- **WHEN** o release protegido publica API e web e as evidências verificam imagens e saúde no SHA candidato
- **THEN** uma mudança revisável atualiza `production_baseline_sha` para esse SHA, e a classificação seguinte considera somente commits posteriores à publicação

#### Scenario: Operação sem alteração de runtime
- **WHEN** uma mudança operacional posterior à publicação não altera arquivos de runtime API/web
- **THEN** o classificador retorna `release_scope=none` e não inicia um novo preflight nem release de API/web

#### Scenario: Release sem comprovação pós-publicação
- **WHEN** o preflight, a CI ou o job de release falha, é ignorado ou não confirma saúde pós-publicação
- **THEN** o baseline anterior permanece intacto
