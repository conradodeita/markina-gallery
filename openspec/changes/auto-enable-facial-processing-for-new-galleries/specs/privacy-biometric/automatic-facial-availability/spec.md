## Purpose

Definir como galerias ativas recebem disponibilidade facial automática quando o ambiente está operacional, preservando bloqueios explícitos, privacidade e controles de produção.

## ADDED Requirements

### Requirement: Disponibilidade facial automática por ambiente

`FACIAL_PROCESSING_ENABLED` SHALL ser um kill switch independente por ambiente. Com ambiente coerente e calibração válida, galerias públicas ativas sem rollout individual SHALL usar `active/general`, sem ativação pelo fotógrafo.

#### Scenario: Nova galeria com ambiente facial habilitado

- **WHEN** o administrador cria uma Galeria pública ativa em ambiente com kill switch habilitado e calibração válida, sem rollout individual
- **THEN** a galeria admite indexação e busca facial conforme os demais gates e o painel informa disponibilidade `active/general`

#### Scenario: Galeria existente sem rollout individual

- **WHEN** uma Galeria pública ativa criada anteriormente é consultada depois que o ambiente facial está habilitado e calibrado
- **THEN** a mesma disponibilidade geral é aplicada imediatamente, sem backfill, nova ativação, duplicação de mídia ou perda de índices existentes

#### Scenario: Ambiente ou calibração indisponível

- **WHEN** o kill switch estiver desligado, a galeria estiver inativa ou a calibração obrigatória de produção não estiver aprovada
- **THEN** o subsistema facial permanece indisponível enquanto upload, navegação e seleção manual continuam saudáveis

### Requirement: Precedência do rollout individual

Rollout individual `prepared`, `suspended` ou `revoked` SHALL bloquear a galeria. Rollout `active` SHALL exigir etapa ativa e versões compatíveis. Um rollout de outro ambiente MUST falhar fechado.

#### Scenario: Bloqueio explícito da galeria

- **WHEN** existe rollout individual `prepared`, `suspended` ou `revoked` para a galeria
- **THEN** novas admissões permanecem bloqueadas nessa galeria mesmo que o kill switch global esteja habilitado

#### Scenario: Rollout individual ativo

- **WHEN** existe rollout individual `active` em etapa ativa e com versões compatíveis
- **THEN** a galeria permanece disponível na etapa persistida e auditável

#### Scenario: Rollout pertence a outro ambiente

- **WHEN** a galeria possui rollout persistido em ambiente diferente do runtime atual
- **THEN** o sistema falha fechado e não aplica disponibilidade geral por ausência no ambiente atual

### Requirement: Gate de nova ativação facial em produção

Homologação MAY permanecer habilitada para validação funcional. Uma nova ativação de produção sem autorização do proprietário MUST manter `FACIAL_PROCESSING_ENABLED=false` até registrar evidências de segurança, privacidade, base legal, calibração, capacidade e recuperação e receber aprovação humana.

#### Scenario: Nova produção sem aprovação de ativação

- **WHEN** um novo ambiente de produção será ativado sem todas as evidências e aprovação humana exigidas
- **THEN** o kill switch permanece desligado e o subsistema facial indisponível

### Requirement: Preservação facial em redeploy de produção

A produção já ativa e autorizada pelo proprietário SHALL preservar `FACIAL_PROCESSING_ENABLED=true` em todo deploy ou redeploy. A release MUST falhar se o alvo definir `false` ou omitir a flag com default desligado.

#### Scenario: Redeploy preserva a busca facial de produção

- **WHEN** uma release atinge a produção facial já ativa e autorizada pelo proprietário
- **THEN** `FACIAL_PROCESSING_ENABLED` continua `true` e a release rejeita alvo que o desabilite ou o redefina como desligado

### Requirement: Interrupção global do processamento facial

Desligar o kill switch SHALL interromper processamento sem migration destrutiva.

#### Scenario: Interrupção pelo kill switch

- **WHEN** o proprietário desliga o kill switch de um ambiente
- **THEN** novas admissões faciais cessam imediatamente, sem apagar índices por migration destrutiva
