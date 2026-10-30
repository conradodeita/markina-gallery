# Spec Delta

## Purpose

Definir como classificar e migrar dados biométricos cifrados vinculados a um `APP_ENV` de origem, preservando finalidade, consentimento, retenção, isolamento por tenant e os gates operacionais de produção.

## ADDED Requirements

### Requirement: Inventário biométrico sanitizado
O sistema SHALL inventariar por categoria e ambiente os objetos biométricos cifrados relevantes sem descriptografar payloads ou emitir valores, IDs, caminhos ou identificadores derivados. Origem, finalidade, consentimento ou retenção não verificáveis MUST bloquear a elegibilidade.

#### Scenario: Inventário encontra dados biométricos na origem
- **WHEN** a coleta somente-leitura identifica objetos cifrados ligados ao ambiente de origem
- **THEN** o relatório apresenta apenas categorias, contagens agregadas e bloqueios sanitizados
- **AND** não lê nem expõe payloads, IDs, caminhos ou valores de clientes

#### Scenario: Diagnóstico operacional complementar de índices
- **WHEN** o coletor protegido consulta a procedência dos embeddings existentes
- **THEN** ele reporta somente contagens de vínculos consistentes, política ausente/inativa, versão de modelo divergente e evidência de rollout
- **AND** os metadados não substituem a autenticação do conjunto nem removem bloqueios de transição
- **AND** recibos anteriores sem o diagnóstico continuam legíveis e uma coleta incompleta não emite diagnóstico parcial

#### Scenario: Metadados necessários não podem ser verificados
- **WHEN** a origem, a finalidade, o consentimento ou a retenção de algum objeto é desconhecida
- **THEN** o sistema marca o conjunto como não elegível e bloqueia fingerprint aprovável
- **AND** não altera nem exclui os objetos

### Requirement: Elegibilidade biométrica para o destino
Somente objetos com origem, finalidade, consentimento aplicável, retenção vigente e autorização documentados SHALL ser elegíveis à re-cifragem para o ambiente de destino. Dados expirados, revogados ou sem autorização MUST permanecer inalterados e bloquear a transição.

#### Scenario: Objeto cumpre os critérios documentados
- **WHEN** todos os critérios de elegibilidade e autorização do destino são comprovados no inventário aprovado
- **THEN** o objeto pode integrar o plano de migração revisável
- **AND** sua inclusão não habilita busca facial nem constitui aprovação para execução

#### Scenario: Objeto expirado, revogado ou sem autorização
- **WHEN** qualquer critério de elegibilidade não é satisfeito
- **THEN** o objeto não é re-cifrado, excluído ou reclassificado por esta operação
- **AND** o bloqueio permanece até tratamento por fluxo e autorização próprios

#### Scenario: Índice de fotografia operacional com autorização do conjunto
- **WHEN** um embedding pertence a uma foto e galeria do mesmo tenant e os metadados de política e rollout comprovam o contexto de origem, autorização operacional e retenção vigente do conjunto
- **THEN** a avaliação usa essa prova vinculada à galeria, sem exigir um consentimento de upload de referência individual para cada embedding
- **AND** a declaração de origem do proprietário isoladamente não preenche a prova técnica nem autoriza uma operação de produção
- **AND** um prazo individual explícito expirado, política revogada ou vínculo divergente continua bloqueando a migração

### Requirement: Re-cifragem preserva identidade e finalidade
Objetos elegíveis SHALL ser re-cifrados entre contextos explícitos de origem e destino, preservando IDs, vínculos de tenant/galeria/cliente, consentimento, finalidade, retenção, auditoria e estado. Texto claro MUST existir somente em memória e payloads ou identificadores derivados MUST NOT aparecer em logs ou recibos.

#### Scenario: Migração elegível concluída
- **WHEN** todos os objetos do plano são válidos nos contextos aprovados de origem e destino
- **THEN** a re-cifragem preserva seus vínculos e metadados de privacidade
- **AND** a verificação pós-migração confirma a leitura no destino sem registrar payloads

#### Scenario: Contexto ou objeto incompatível
- **WHEN** uma chave, contexto ou objeto não pode ser validado
- **THEN** a operação aborta sem liberar estado parcial nem alterar a finalidade, o consentimento ou os vínculos

### Requirement: Atomicidade e recuperação dos dados biométricos
A operação SHALL exigir backup cifrado verificável antes da primeira escrita e impedir que consumidores observem uma migração parcial. Falhas MUST manter ou restaurar o conjunto de origem sem perda de IDs ou metadados.

#### Scenario: Falha durante a re-cifragem
- **WHEN** ocorre erro de concorrência, persistência ou validação durante a operação
- **THEN** a transação ou recuperação restaura um conjunto consistente no contexto de origem
- **AND** consumidores permanecem pausados conforme o plano aprovado até a verificação da recuperação

#### Scenario: Recuperação validada
- **WHEN** a restauração autenticada conclui e as verificações de consistência passam
- **THEN** o contexto e os dados biométricos anteriores permanecem utilizáveis
- **AND** nenhum registro ou vínculo é recriado ou descartado

### Requirement: Gates de produção permanecem independentes
Esta operação MUST NOT habilitar busca facial em produção nem alterar sua flag. `MERCADOPAGO_ALLOW_LIVE_PAYMENTS` SHALL permanecer fechado; a transição APP_ENV só poderá prosseguir após nova coleta provar ausência de dados biométricos vinculados à origem e aprovação dos demais gates.

#### Scenario: Migração biométrica concluída
- **WHEN** a re-cifragem aprovada termina com sucesso
- **THEN** a busca facial conserva sua flag anterior e não processa dados novos
- **AND** pagamentos reais continuam bloqueados até aprovação própria da change de liberação

#### Scenario: Plano ou autorização operacional ausente
- **WHEN** inventário atual, fingerprint, backup, plano de impacto/recuperação ou aprovação específica está ausente ou divergente
- **THEN** a operação de produção falha fechada antes da primeira escrita
- **AND** a busca facial e o gate de pagamentos permanecem inalterados
