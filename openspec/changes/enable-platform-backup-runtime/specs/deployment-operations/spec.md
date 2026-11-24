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

### Requirement: Preparação e restauração protegidas do suporte de preflight

O suporte do preflight SHALL usar operações fixas e protegidas, CI verde da `main` no SHA exato, fingerprint atual e aprovação `production` para mutações. A preparação SHALL preservar cópias/recibos root-only e alterar somente ponte, forced command e `refs/remotes/origin/main`. SHALL oferecer compensação única e restauração por recibo. MUST NOT aceitar caminhos/comandos arbitrários nem alterar checkout/aplicações.

#### Scenario: Inventário específico da preparação

- **WHEN** o inventário read-only de suporte coleta identidade do host/remoto, SHA da main, referência local, metadados/hash dos executáveis e identidade agregada dos containers
- **THEN** SHALL emitir somente fingerprint específica de suporte e resumo sanitizado; MUST NOT tratar essa fingerprint como inventário/fingerprint do runtime de backup
- **AND** se a coleta for incompleta, não emitir fingerprint nem autorizar preparação

#### Scenario: Resposta de docker inspect contém campos com tipos inválidos

- **WHEN** `support-inventory` recebe campos `Id`, `Image`, `State.Status` ou `State.StartedAt` ausentes ou com tipo diferente de string
- **THEN** SHALL abortar com somente `support_container_inventory_invalid`, sem fingerprint ou precondição aprovada
- **AND** valores do JSON, IDs/imagens de containers, exceção, caminho e saída de comando MUST NOT aparecer no log

#### Scenario: Inventário do suporte classifica as pastas fixas de persistência

- **WHEN** support-inventory inspecionar o estado para preparação
- **THEN** SHALL ler sem mutação os diretórios fixos de estado e de cópias e incluir na fingerprint somente ready, creatable, parent_invalid, directory_invalid ou unavailable
- **AND** SHALL omitir paths, conteúdo, UID/GID e modos brutos do resumo do workflow
- **AND** MUST NOT criar, chmod, substituir ou limpar esses diretórios durante o inventário

#### Scenario: Persistência insegura aborta antes da preparação

- **WHEN** o estado revalidado de qualquer diretório fixo não for ready ou creatable
- **THEN** prepare-support SHALL abortar antes de buscar candidatos, criar diretórios/cópias/recibos ou alterar os três alvos
- **AND** SHALL emitir somente o código allowlisted correspondente e não criar recibo de preparação

#### Scenario: Preparação com estado ainda aprovado

- **WHEN** a fingerprint revisada, o SHA de main/CI, os alvos fixos e a identidade dos containers forem revalidados sob o lock comum
- **THEN** SHALL preservar e verificar os estados anteriores em cópias e recibo root-only, atualizar `refs/remotes/origin/main` por compare-and-swap e trocar atomicamente apenas a ponte e o forced command
- **AND** SHALL confirmar hashes/blobs, owner/mode/link, allowlist e identidade invariável dos containers

#### Scenario: Divergência antes da primeira mutação

- **WHEN** host, remoto, SHA/CI, ref anterior, executável, fingerprint, lock ou containers divergir do preflight
- **THEN** a operação MUST abortar sem alterar os três alvos e sem emitir fingerprint aprovada para a preparação

#### Scenario: Referência antiga não pode ser restaurada com segurança

- **WHEN** `refs/remotes/origin/main` existir, mas seu objeto estiver ausente ou não for ancestral do SHA alvo aprovado
- **THEN** a operação MUST abortar antes de criar cópias ou recibo e sem alterar a ref ou os executáveis

#### Scenario: Cópia, recibo ou staging fixo já existe

- **WHEN** um nome gerado para cópia/recibo colidir ou qualquer staging fixo da preparação/restauração existir
- **THEN** a operação MUST abortar sem sobrescrever/remover o artefato nem alterar os três alvos

#### Scenario: Falha parcial e compensação não comprovada

- **WHEN** qualquer troca falhar após a primeira mutação ou a verificação pós-troca falhar
- **THEN** SHALL tentar uma única compensação na ordem inversa, somente para alvos cujo conteúdo ainda seja exatamente o estado original ou o candidato do recibo
- **AND** se qualquer estado for inesperado, a compensação falhar ou a prova não fechar, MUST NOT sobrescrever esse estado, repetir ou limpar; SHALL preservar cópias/recibos e emitir somente `support_preparation_rollback_unverified`

#### Scenario: Restaurar preparação concluída

- **WHEN** o operador pedir restauração após preparação concluída e apresentar digest do recibo, fingerprint atual, CI verde no SHA exato e aprovação `production`
- **THEN** SHALL criar cópias/recibo de restauração antes de alterar, restaurar em ordem inversa os dois executáveis e `refs/remotes/origin/main`, e confirmar exatamente o estado anterior e os containers
- **AND** uma falha pós-troca SHALL tentar uma única compensação ao estado imediatamente anterior à restauração; falha ou incerteza emite somente `support_restore_fallback_unverified`, preservando estado observado e todos os recibos/cópias
- **AND** `restore-wrapper` do backup MUST NOT ser aceito como recibo ou substituto deste fluxo
