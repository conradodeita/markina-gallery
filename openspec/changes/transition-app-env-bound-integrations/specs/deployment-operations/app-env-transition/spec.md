# Spec Delta

## Purpose

O sistema SHALL inventariar e migrar o contexto de ambiente das integrações da Markina Gallery sem expor valores secretos, preservando isolamento por tenant, identificadores e operação financeira existente. Mudanças de produção SHALL usar fingerprint e backup aprovados e admitir recuperação verificável.

## ADDED Requirements

### Requirement: Inventário ambiental agregado e redigido
O preflight SHALL identificar o ambiente de origem, o ambiente alvo, todos os consumidores de `APP_ENV` e contagens agregadas de credenciais/configurações e dados cifrados vinculados ao ambiente, sem revelar valores, payloads cifrados, IDs de tenant, chaves, tokens ou conteúdo de arquivos. Resultado incompleto ou desconhecido MUST impedir a emissão de fingerprint aprovável.

#### Scenario: Inventário completo sem segredos
- **WHEN** o preflight lê os serviços e metadados necessários
- **THEN** o relatório contém somente categorias ambientais, contagens, versões, schema, saúde, portas e bloqueios sanitizados
- **AND** nenhum segredo, identificador de tenant ou payload cifrado aparece em logs ou artefatos

#### Scenario: Fonte ausente, inválida ou incompleta
- **WHEN** uma fonte ambiental ou categoria de credenciais não pode ser verificada
- **THEN** o preflight não emite fingerprint aprovável e nenhuma configuração ou dado é alterado

#### Scenario: Consumidor de ambiente ou dado cifrado não classificado
- **WHEN** código, serviço, configuração ou conjunto de dados cifrados vinculado ao ambiente não consta da matriz suportada
- **THEN** o inventário marca o bloqueio sanitizado e não autoriza a troca global de ambiente

### Requirement: Re-cifragem preserva credenciais e identidade por tenant
A migração SHALL re-cifrar envelopes elegíveis do ambiente de origem para o ambiente alvo, validando cada envelope com seu tenant, credencial, chave e contexto originais e preservando o valor e a identidade associados. Valores em texto claro MUST permanecer somente em memória durante a operação, sem log, arquivo auxiliar ou saída.

#### Scenario: Re-cifragem completa
- **WHEN** todos os envelopes inventariados são válidos e as chaves de origem e alvo estão disponíveis
- **THEN** cada envelope elegível é validado no contexto alvo e os IDs, vínculos de tenant, recebedor e snapshots financeiros permanecem inalterados
- **AND** nenhuma credencial é exibida, exportada ou enviada ao provedor

#### Scenario: Envelope ou chave incompatível
- **WHEN** um envelope é corrompido, pertence a outro contexto, está ausente ou não pode ser descriptografado com a chave esperada
- **THEN** a migração aborta sem atualização parcial e preserva o conjunto anterior de envelopes

### Requirement: Integrações externas não são copiadas entre ambientes
O procedimento SHALL tratar credenciais e configurações externas de WhatsApp, e-mail e facial separadamente dos envelopes Mercado Pago. Ele MUST NOT copiar valores secretos, reclassificar credenciais ou presumir equivalência entre ambientes; divergência SHALL bloquear a integração afetada e a transição global enquanto sua classificação não for resolvida, sem revelar valores.

#### Scenario: Credencial externa ainda vinculada à origem
- **WHEN** a configuração externa identifica ambiente diferente do alvo
- **THEN** o procedimento preserva o arquivo e os valores existentes, registra apenas um bloqueio sanitizado e não ativa esse provedor no alvo

#### Scenario: Credencial externa confirmada para o alvo
- **WHEN** o operador confirma no plano aprovado que a credencial existente pertence ao ambiente alvo e a validação própria do provedor passa
- **THEN** o vínculo ambiental pode ser atualizado sem copiar ou registrar o valor secreto

### Requirement: Dados biométricos cifrados permanecem fora da migração
Esta operação SHALL NOT descriptografar, re-cifrar, remover ou reclassificar embeddings, referências, localizadores ou notificações biométricas vinculados ao `APP_ENV`. A existência de dados biométricos cifrados no contexto de origem MUST bloquear a troca global de ambiente e exigir change e autorização próprias antes de qualquer migração ou exclusão.

#### Scenario: Inventário encontra dados biométricos cifrados
- **WHEN** o inventário encontra registros, arquivos ou filas biométricos cifrados sob o ambiente de origem
- **THEN** registra apenas contagem agregada e categoria de bloqueio, não acessa o payload e não emite fingerprint aprovável para a transição

#### Scenario: Nenhum dado biométrico cifrado depende da origem
- **WHEN** a ausência desses dados é comprovada e o subsistema está desligado ou validado para o alvo
- **THEN** a transição pode prosseguir sem alterar configuração, chaves, dados ou filas faciais

### Requirement: Transição protegida sem alteração financeira
A transição de produção SHALL exigir inventário completo, backup recuperável, plano de impacto e fingerprint exato revisados e aprovados antes de qualquer mutação. Durante a migração, o gate `MERCADOPAGO_ALLOW_LIVE_PAYMENTS` SHALL permanecer fechado; PIX, pedidos, pagamentos, IDs, snapshots e histórico MUST permanecer preservados, e nenhuma cobrança ou mensagem externa de teste pode ser emitida.

#### Scenario: Fingerprint aprovado e estável
- **WHEN** a operação mutável recebe a aprovação do fingerprint apresentado e o inventário repetido permanece idêntico
- **THEN** a transição pode iniciar somente nos serviços, arquivos e registros da Markina listados no plano
- **AND** o gate de pagamentos reais permanece fechado

#### Scenario: Fingerprint mudou ou aprovação ausente
- **WHEN** o fingerprint diverge, falta aprovação ou o inventário aponta recurso fora do escopo
- **THEN** a operação aborta antes de alterar arquivos, serviços ou banco

### Requirement: Recuperação coerente do contexto anterior
A operação SHALL manter backup cifrado verificável dos registros e configuração necessários e uma recuperação que restaure o contexto ambiental anterior junto com seus envelopes, sem recriar IDs nem apagar histórico financeiro. Falha ou interrupção MUST deixar a operação em estado identificável e impedir novos pagamentos até a consistência ser confirmada.

#### Scenario: Falha durante a transição
- **WHEN** a atualização de envelopes, configuração ou saúde dos serviços falha
- **THEN** a recuperação restaura configuração e envelopes compatíveis com o ambiente anterior antes de liberar tráfego normal
- **AND** pagamentos reais permanecem bloqueados até a verificação de consistência

#### Scenario: Recuperação validada
- **WHEN** a restauração é concluída e seus checksums e verificações de contexto passam
- **THEN** credenciais e integrações usam novamente o contexto anterior, e pedidos, pagamentos e histórico permanecem idênticos
