## Purpose

Definir como galerias ativas recebem disponibilidade facial automática quando o ambiente está operacional, preservando bloqueios explícitos, privacidade e controles de produção.

## ADDED Requirements

### Requirement: Disponibilidade facial automática por ambiente

O sistema SHALL manter `FACIAL_PROCESSING_ENABLED` como kill switch técnico independente por ambiente. Quando o kill switch estiver habilitado, o ambiente estiver coerente e a calibração exigida estiver válida, toda Galeria pública ativa sem rollout individual SHALL possuir disponibilidade facial efetiva `active/general`, sem preparação ou ativação manual pelo fotógrafo. Um rollout individual persistido em estado `prepared`, `suspended` ou `revoked` SHALL prevalecer como bloqueio explícito da galeria; um rollout `active` SHALL exigir etapa ativa e versões compatíveis. Homologação MAY permanecer habilitada para validação funcional, mas produção MUST iniciar desligada e somente SHALL ser habilitada após evidência registrada de segurança, privacidade, base legal, calibração, capacidade, recuperação e aprovação humana. O kill switch SHALL permitir interrupção global imediata sem migration destrutiva.

#### Scenario: Nova galeria com ambiente facial habilitado

- **WHEN** o administrador cria uma Galeria pública ativa em ambiente com kill switch habilitado e calibração válida, sem rollout individual
- **THEN** a galeria admite indexação e busca facial conforme os demais gates e o painel informa disponibilidade `active/general`

#### Scenario: Galeria existente sem rollout individual

- **WHEN** uma Galeria pública ativa criada anteriormente é consultada depois que o ambiente facial está habilitado e calibrado
- **THEN** a mesma disponibilidade geral é aplicada imediatamente, sem backfill, nova ativação, duplicação de mídia ou perda de índices existentes

#### Scenario: Bloqueio explícito da galeria

- **WHEN** existe rollout individual `prepared`, `suspended` ou `revoked` para a galeria
- **THEN** novas admissões permanecem bloqueadas nessa galeria mesmo que o kill switch global esteja habilitado

#### Scenario: Rollout individual ativo

- **WHEN** existe rollout individual `active` em etapa ativa e com versões compatíveis
- **THEN** a galeria permanece disponível na etapa persistida e auditável

#### Scenario: Ambiente ou calibração indisponível

- **WHEN** o kill switch estiver desligado, a galeria estiver inativa ou a calibração obrigatória de produção não estiver aprovada
- **THEN** o subsistema facial permanece indisponível enquanto upload, navegação e seleção manual continuam saudáveis
