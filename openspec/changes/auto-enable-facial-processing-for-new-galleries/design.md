## Context

Veja `proposal.md`. Hoje `rollout_is_active` falha fechado quando não encontra uma linha em `facial_rollout`; por isso uma galeria recém-criada não admite jobs embora o ambiente esteja habilitado. O mesmo predicado atende admissão e execução, e o painel deriva seu rótulo do payload de rollout.

O roadmap consolidou que o fotógrafo não prepara nem ativa política técnica por galeria. Ao mesmo tempo, kill switch, calibração de produção, suspensão/revogação explícita, consentimento da cliente, retenção e isolamento continuam obrigatórios.

## Goals / Non-Goals

**Goals:**

- tornar a disponibilidade geral efetiva para galerias ativas sem registro individual;
- corrigir galerias existentes e futuras na mesma regra, sem mutação retroativa;
- manter bloqueios explícitos e o kill switch como controles de precedência superior;
- apresentar estado administrativo coerente com a disponibilidade efetiva.

**Non-Goals:**

- criar registros em massa ou migration;
- iniciar reprocessamento automático do acervo já concluído;
- remover consentimento, representação, retenção ou autorização de acesso da cliente;
- reativar rollout explicitamente suspenso ou revogado.

## Decisions

### 1. Resolver disponibilidade por precedência, sem criar rollout implícito no banco

A resolução SHALL seguir esta ordem: kill switch/calibração/galeria ativa; depois rollout individual, quando existir; por fim disponibilidade `general` quando não existir registro. Rollout explícito somente permite execução se estiver `active`, em etapa ativa e com versões coerentes; qualquer outro estado bloqueia.

Isso evita escrita em endpoint GET, concorrência de criação, escolha artificial de aprovador e backfill operacional. A alternativa de criar automaticamente uma linha `active` ao salvar cada galeria não corrige as galerias já existentes e introduz uma aprovação fictícia. A alternativa de uma migration de dados foi rejeitada porque a disponibilidade depende de configuração e calibração do ambiente em runtime.

### 2. Representar o padrão efetivo como `active/general` no payload

Quando não houver rollout persistido e a disponibilidade efetiva for verdadeira, o payload administrativo SHALL sintetizar somente o estado operacional `active/general`. Nenhum UUID, aprovador ou registro inexistente será inventado. Se a disponibilidade for falsa, a ausência continuará aparecendo como `unavailable`.

Assim, a interface existente deixa de exibir “Rollout não disponível” e passa a refletir o comportamento real sem mudança visual duplicada.

### 3. Preservar rollouts persistidos como exceção explícita

Registros `prepared`, `suspended` e `revoked` continuam bloqueando, e registros `active` mantêm sua etapa. Isso preserva suspensão por incidente e rollout controlado onde ele foi configurado, sem permitir que o padrão geral reative uma galeria bloqueada.

### 4. Validar o caminho completo com testes focados

Os contratos deverão cobrir ausência de rollout, galeria inativa, flag desligada, calibração de produção ausente, estados explícitos e payload do painel. Um teste de integração da indexação confirmará que uma foto elegível de galeria sem rollout individual recebe job quando o ambiente está habilitado.

## Risks / Trade-offs

- [Ativar mais galerias que no modelo antigo] → limitar o padrão a galerias ativas e manter kill switch, calibração e bloqueios explícitos antes de qualquer admissão.
- [Estado sintetizado ser confundido com registro auditável] → expor apenas disponibilidade/etapa operacional e nunca inventar identificadores ou aprovadores.
- [Rollout antigo incompatível bloquear uma galeria] → manter falha fechada intencional e permitir que a operação existente suspenda, atualize ou revogue o registro conscientemente.

## Migration Plan

1. Publicar a resolução de disponibilidade e o payload coerente sem migration.
2. Confirmar em homologação que galerias novas e já existentes sem rollout aparecem como `active/general` e admitem jobs.
3. Preservar `FACIAL_PROCESSING_ENABLED=true`, limite de referência e workers existentes.
4. Em rollback, restaurar apenas o SHA anterior; banco, mídia e índices não exigem restauração ou downgrade.
