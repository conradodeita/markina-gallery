# Spec Delta

## ADDED Requirements

### Requirement: Ativação controlada de pagamentos reais Mercado Pago
A liberação geral SHALL permitir pagamentos reais Orders para fotógrafos elegíveis sem habilitar automaticamente contas, configurações ou galerias de todos os tenants.

#### Scenario: Gate de produção ativado
- **WHEN** a liberação aprovada ativa `MERCADOPAGO_ALLOW_LIVE_PAYMENTS` em produção
- **THEN** somente contas de produção válidas e habilitadas pelo respectivo fotógrafo podem iniciar novas cobranças, e a restrição das contas de teste permanece intacta

#### Scenario: Fotógrafo ainda não configurou sua conta
- **WHEN** o gate de produção está ativo mas um tenant não tem conta real válida e habilitada
- **THEN** o checkout desse tenant não oferece Mercado Pago e os demais meios permanecem conforme sua configuração

#### Scenario: Evidências sandbox reaproveitadas
- **WHEN** a change é preparada para liberação geral após a bateria sandbox aprovada pelo proprietário
- **THEN** essas evidências são reaproveitadas e não se repete a bateria de pagamentos sem mudança técnica relevante

#### Scenario: Smoke da ativação
- **WHEN** a configuração de produção é aplicada
- **THEN** o operador confirma SHA e serviços alvo, saúde local e HTTPS, estado do gate e ausência de credenciais no Git, sem emitir cobrança real de teste

#### Scenario: Reversão do gate de novas cobranças
- **WHEN** a verificação operacional detecta falha após abrir a liberação
- **THEN** novas emissões reais são fechadas pelo gate global enquanto consulta, webhook e reconciliação de tentativas já enviadas continuam ativos
