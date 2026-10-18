# deployment-operations Specification

## ADDED Requirements

### Requirement: Identidade web é vinculada à imagem ativa
O procedimento SHALL identificar o frontend por ID imutável Docker e recibo com SHA de origem, hash Compose e checkout. Releases app e web SHALL consumir e publicar o mesmo contrato. Marcadores legados MUST NOT ser prova isolada. Adoção legada SHALL exigir SHA/ID explícitos, evidência de origem, inventário e aprovação antes da escrita.

#### Scenario: App seguido de web e web seguido de app
- **WHEN** um fluxo publica após o outro
- **THEN** ambos conferem o recibo com a imagem ativa e preservam a versão API independente quando só o frontend mudou

#### Scenario: Recibo ausente ou divergente
- **WHEN** falta identidade verificável ou ela não coincide com runtime
- **THEN** release SHALL falhar sem mutação e exigir adoção explícita ou investigação, sem copiar marcadores

### Requirement: Inventários de release não escrevem no host
Os inventários app/web SHALL NOT criar ou truncar locks, criar temporários, buscar Git, atualizar índice/refs, criar tags ou modificar estado. Alvo ausente SHALL bloquear sem escrita. Mutação SHALL exigir SHA aprovado, lock compartilhado existente e revalidação integral antes da primeira escrita.

#### Scenario: Consulta com lock ocupado ou ausente
- **WHEN** um inventário consulta o runtime
- **THEN** não abre lock para escrita nem tenta adquiri-lo e apresenta apenas snapshot; a execução mutável exige lock exclusivo disponível

#### Scenario: SHA ou aprovação incorretos
- **WHEN** alvo, fingerprint ou escopo diferem do aprovado
- **THEN** nenhuma imagem, checkout, marcador ou serviço SHALL ser modificado

### Requirement: Recuperação web restaura identidade comprovada
Release web SHALL preservar a imagem ativa por ID conferido e guardar recibo/checkout anterior antes do build. Rollback e recuperação contingencial SHALL verificar imagem salva antes de mudar checkout e conferir ID restaurado, configuração, saúde e HTTPS. Fluxo web SHALL NOT alterar API, workers, banco, Redis, nginx, proxy, volumes ou fotografias.

#### Scenario: Build falha
- **WHEN** a construção falha antes de recriar web
- **THEN** runtime anterior permanece e o registro durável permite recuperar checkout/tag sem supor sucesso

#### Scenario: Healthcheck ou recriação falha
- **WHEN** web fica unhealthy, ausente ou usa imagem incorreta
- **THEN** tentativa permanece pendente e recuperação aprovada restaura somente o ID anterior, sem dependências; falha de recuperação mantém bloqueio

#### Scenario: Imagem salva ausente ou tag divergente
- **WHEN** a recuperação não tem imagem por ID ou sua tag aponta a outro conteúdo
- **THEN** a operação SHALL abortar antes de trocar checkout ou recriar serviço

#### Scenario: Concorrência ou outro serviço muda
- **WHEN** outro fluxo detém lock, há tentativa não concluída ou o snapshot não-web muda durante build
- **THEN** a publicação SHALL abortar antes da troca e manter evidências para investigação

### Requirement: Suporte de coordenação mantém allowlist exata
O verificador app SHALL admitir somente `scripts/deploy-prod-state.sh` e `scripts/test_prod_release_state.py` como novos caminhos exatos de suporte/teste desta coordenação além da allowlist existente, preservando baseline, blobs de runtime, schema e gates de aprovação. Alterações apenas operacionais SHALL ser classificadas como none e não acionar operações remotas no merge.

#### Scenario: Integração de engenharia
- **WHEN** a main recebe somente esta correção de procedimento e documentação
- **THEN** CI e revisão verificam release_scope=none e jobs de ambiente SHALL permanecer ignorados
