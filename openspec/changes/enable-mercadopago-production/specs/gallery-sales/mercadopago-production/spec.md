# Spec Delta

## Purpose

Define a disponibilidade de pagamentos reais Mercado Pago Orders para fotógrafos que configurem e habilitem a própria conta de produção, preservando o isolamento por tenant e a restrição das credenciais de teste.

## ADDED Requirements

### Requirement: Conta de produção própria por fotógrafo
O sistema SHALL permitir que cada fotógrafo use somente a própria conta Mercado Pago de produção validada e vinculada ao seu tenant.

#### Scenario: Fotógrafo configura credenciais de produção próprias
- **WHEN** o fotógrafo autenticado configura credenciais de produção e o servidor confirma a identidade da conta recebedora
- **THEN** a conta fica vinculada exclusivamente ao tenant autenticado e pode ser habilitada sem expor credenciais

#### Scenario: Identidade da conta não corresponde
- **WHEN** a conta verificada pelo Mercado Pago não corresponde ao recebedor esperado da configuração
- **THEN** a configuração permanece indisponível para novas cobranças e nenhuma credencial ou conta de outro tenant é reutilizada

### Requirement: Disponibilidade real habilitada por tenant
O sistema SHALL disponibilizar cobranças reais somente quando a liberação global de produção estiver ativa e o fotógrafo tiver habilitado uma conta de produção válida em seu próprio tenant.

#### Scenario: Fotógrafo habilita sua conta de produção
- **WHEN** o gate de produção está ativo e a conta de produção do fotógrafo está válida e habilitada
- **THEN** clientes autorizados daquele tenant podem selecionar Mercado Pago e iniciar checkout com o snapshot e recebedor daquela conta

#### Scenario: Outro fotógrafo ainda não configurou Mercado Pago
- **WHEN** a liberação geral está ativa, mas outro fotógrafo não configurou ou não habilitou uma conta própria válida
- **THEN** seus clientes não recebem Mercado Pago como método disponível e continuam vendo os métodos habilitados para aquele tenant

#### Scenario: Gate global fechado
- **WHEN** o gate de produção está fechado
- **THEN** nenhuma conta de produção pode emitir nova cobrança, enquanto consulta, notificações e reconciliação de tentativas existentes permanecem disponíveis

### Requirement: Contas de teste permanecem restritas
Em ambiente operacional, credenciais identificadas como teste SHALL continuar limitadas aos pares tenant/cliente explicitamente permitidos pelo servidor, independentemente da liberação de contas de produção.

#### Scenario: Cliente fora da allowlist de teste
- **WHEN** uma conta de teste é usada por cliente ou tenant fora da allowlist operacional
- **THEN** carrinho e envio recusam nova cobrança sem consumir a seleção nem impedir a reconciliação de tentativas já enviadas

#### Scenario: Conta de teste e conta real coexistem
- **WHEN** o gate de produção é aberto para contas reais
- **THEN** a abertura não amplia a allowlist de contas de teste nem permite reutilizar credenciais de teste como produção

### Requirement: Isolamento de dados e recebimentos por fotógrafo
Cada tentativa, pedido, credencial, webhook e reconciliação Mercado Pago SHALL permanecer associado ao tenant e à conta recebedora que originaram aquela tentativa.

#### Scenario: Cliente paga em galeria de fotógrafo configurado
- **WHEN** o cliente inicia pagamento numa galeria autorizada
- **THEN** a tentativa usa somente a conta ativa do fotógrafo responsável, e estados, identificadores e receita permanecem visíveis apenas nos escopos autorizados desse tenant

#### Scenario: Atualização financeira de outro tenant
- **WHEN** uma notificação ou consulta referencia uma conta, tentativa ou pedido de outro tenant
- **THEN** a atualização não altera nem revela dados financeiros fora do tenant correspondente

### Requirement: Disponibilidade independente do PIX
A habilitação de cobranças reais Mercado Pago SHALL permanecer independente da configuração e disponibilidade do PIX manual existente.

#### Scenario: Fotógrafo oferece os dois métodos
- **WHEN** o fotógrafo habilita PIX manual e sua conta Mercado Pago de produção
- **THEN** clientes podem escolher cada método e seus pagamentos, estados e configurações permanecem separados

#### Scenario: Fotógrafo desabilita um método
- **WHEN** o fotógrafo desabilita Mercado Pago ou PIX
- **THEN** somente o método correspondente deixa de ser oferecido e os registros e configurações anteriores permanecem preservados
