# media-storage/platform-backup-recovery Specification

## ADDED Requirements

### Requirement: Backup independente do arquivo de mídia

O sistema SHALL manter backup e arquivamento de mídia como operações distintas, com políticas, estados, manifestos e procedimentos de restauração independentes.

#### Scenario: Duas rotinas observadas

- **WHEN** um administrador consulta backup e arquivo de mídia
- **THEN** cada estado identifica sua rotina e não infere integridade de uma pela conclusão da outra

### Requirement: Execução rastreável e verificável

Cada backup SHALL registrar origem, escopo, instante, resultado, integridade e proteção criptográfica. Upload concluído MUST NOT equivaler a cópia restaurável.

#### Scenario: Cópia enviada sem restore comprovado

- **WHEN** o upload remoto terminou mas a reabertura ou restauração isolada não foi comprovada
- **THEN** o backup permanece não verificado e não é elegível para substituir/remover outra cópia

### Requirement: Recuperação isolada sem perda de origem

O sistema SHALL validar schema, identidade, integridade e escopo antes de restaurar em ambiente isolado. MUST NOT executar restore destrutivo em produção para demonstrar funcionamento.

#### Scenario: Backup inválido

- **WHEN** checksum, chave, schema ou tenant do conjunto não corresponde ao manifesto
- **THEN** a restauração é recusada antes de escrever dados e a evidência da falha é registrada sem segredos

### Requirement: Retenção configurável

A política de retenção SHALL ser configurável pelo proprietário e MUST NOT excluir a única cópia comprovadamente restaurável.

#### Scenario: Expurgo sem outra cópia íntegra

- **WHEN** uma cópia é candidata à retenção, mas não há outra cópia verificada e restaurável
- **THEN** o sistema mantém a cópia e registra o impedimento

### Requirement: Política global aprovada e escopo inicial

O sistema SHALL planejar backup diário global de todos os tenants, retenção de 7 diários, 4 semanais e 3 mensais e ensaio mensal. RPO de 24 horas e RTO de 8 horas SHALL ser metas sujeitas a medição, não SLA comprovado.

#### Scenario: Novo tenant entra na plataforma

- **WHEN** o próximo backup global é produzido
- **THEN** seus dados do banco entram no mesmo conjunto dos demais tenants, sem criar 7/4/3 cópias separadas para cada fotógrafo

### Requirement: Escopo global inicial e limites de recuperação

O pacote inicial SHALL incluir PostgreSQL completo e configurações essenciais cifradas, com dados pessoais, financeiros e biométricos existentes no banco. Arquivos de fotos/biometria, sessões WhatsApp e recuperação lógica por tenant MUST permanecer fora desta etapa.

#### Scenario: Exibir resultado de recuperação inicial

- **WHEN** o banco e as configurações cifradas são reabertos com sucesso
- **THEN** o relatório delimita o escopo global e não apresenta arquivos de fotos, biometria ou WhatsApp como recuperados

### Requirement: Arquivo autenticado e proveniência vinculada

O arquivo SHALL ser cifrado com AES-256-GCM e AAD versionado que vincule instalação UUID, backup UUID, ambiente, schema e instante UTC. A chave MUST ser fornecida por configuração protegida do chamador e MUST NOT ser persistida no arquivo ou catálogo. A abertura SHALL autenticar o arquivo completo em staging privado antes de liberar bytes ao restaurador, validando o contexto esperado e recusando tamanho excedido, truncamento e adulteração.

#### Scenario: Cabeçalho ou tag adulterados

- **WHEN** a abertura encontra tag inválida, contexto/schema divergente ou arquivo truncado
- **THEN** nenhum plaintext é entregue ao restaurador e o destino de recuperação não recebe escrita

### Requirement: Catálogo durável e cópias retomáveis

O coordenador local SHALL registrar eventos append-only e estados distintos de preparação, cópia parcial, enviada, reaberta, recuperação comprovada e falha. A agenda diária SHALL retomar o mesmo backup/artefato para o dia UTC e recusar conflito de identidade/checksum. Um store SHALL preservar objetos finais imutáveis e retomar parcial somente após validar seu prefixo contra o ciphertext original.

#### Scenario: Processo interrompido durante envio

- **WHEN** a execução seguinte encontra um parcial persistido
- **THEN** valida o mesmo backup, origem e prefixo antes de continuar, sem sobrescrever outra cópia ou promover envio a recuperável

### Requirement: Destinos isolados e independência comprovável

A restauração global SHALL exigir destino explicitamente descartável e vazio, diferente da origem e fora de ambiente protegido. Configuração recuperada MUST NOT ser aplicada ao runtime. Retenção SHALL selecionar a união de pontos por dia, semana ISO e mês, preservando o último recuperável; qualquer remoção exige outra cópia independente do mesmo conjunto com restore comprovado. Stores sintéticos MUST NOT ser apresentados como prova de independência real.

#### Scenario: Destino já contém dados

- **WHEN** o operador solicita recuperação global para um destino não vazio ou para a origem
- **THEN** a operação é recusada antes de executar restauração de banco

### Requirement: Implementação e ensaios locais sem ativação produtiva

O coordenador inicial SHALL operar somente em ambiente local/teste, com adapters sintéticos e erros sanitizados. Chamadas reais Drive, segunda cópia externa, chave real, expurgo e publicação permanecem condicionados aos gates operacionais existentes. A indisponibilidade desses recursos MUST NOT impedir a implementação local independente nem ser simulada como validação produtiva.

#### Scenario: Configuração de produção apresentada ao coordenador local

- **WHEN** o chamador tenta operar em ambiente protegido
- **THEN** a operação é recusada antes de abrir dump, storage, chave persistente ou destino de banco
