# billing/mercadopago-credit-purchases Specification

## ADDED Requirements

### Requirement: Ordem distinta para compra de créditos

O sistema SHALL criar uma compra própria de créditos com tenant comprador, pacote, quantidade, preço congelado e conta recebedora do proprietário resolvidos no servidor. A operação MUST NOT ser modelada como pedido ou item de fotografia, nem aceitar tenant, conta recebedora, pacote, quantidade ou preço enviados pelo browser como autoridade.

#### Scenario: Pacote alterado durante checkout

- **WHEN** um pacote muda ou é desativado depois que a ordem foi preparada
- **THEN** a ordem mantém o snapshot aprovado ou é recusada antes do envio, sem alterar retroativamente preço ou quantidade

#### Scenario: Compra de fotografias permanece independente

- **WHEN** uma cliente paga fotos enquanto um fotógrafo compra créditos
- **THEN** cada operação mantém ordem, pagador, recebedor, saldo, status e histórico próprios

#### Scenario: Tenant comprador e recebedor distintos

- **WHEN** um fotógrafo tenant compra um pacote
- **THEN** a compra registra o tenant autenticado como comprador e vincula a conta Mercado Pago configurada no tenant associado ao proprietário como recebedora

### Requirement: Conta recebedora configurada pelo proprietário

O recebedor SHALL ser a conta Mercado Pago Orders ativa e configurada pelo proprietário global no tenant associado à sua identidade. O servidor MUST resolver proprietário e conta sem confiar no tenant ou na conta enviados pelo comprador. A compra MUST NOT criar credencial global paralela nem revelar segredos.

#### Scenario: Conta do proprietário disponível

- **WHEN** a conta Mercado Pago configurada pelo proprietário está ativa e disponível
- **THEN** o checkout transparente dentro da plataforma cria a Order pela integração Orders existente usando essa conta

#### Scenario: Conta do comprador não substitui a do proprietário

- **WHEN** o tenant comprador tem credenciais Mercado Pago próprias
- **THEN** a ordem de créditos usa a conta do proprietário como recebedora e não consulta as credenciais do comprador

#### Scenario: Conta do proprietário indisponível

- **WHEN** a conta Mercado Pago do proprietário está ausente, desabilitada ou indisponível
- **THEN** o checkout não cria Order, não usa outra conta nem oferece PIX interno, e nenhuma carteira recebe saldo

### Requirement: Mercado Pago é o único provedor padrão para créditos

A compra de créditos SHALL apresentar Mercado Pago como único provedor habilitado por padrão. O PIX interno do sistema MUST NOT ser oferecido nessa compra; métodos nativos do checkout Mercado Pago permanecem associados ao provedor Mercado Pago.

#### Scenario: Preferência de pagamento de créditos

- **WHEN** o fotógrafo abre o checkout de um pacote e a conta do proprietário está disponível
- **THEN** Mercado Pago aparece como provedor padrão e a configuração `pix_enabled` do sistema não habilita uma opção PIX separada para créditos

### Requirement: Crédito somente após confirmação autoritativa

Retorno de navegador, webhook não autenticado ou estado pendente MUST NOT disponibilizar créditos. O backend SHALL validar a notificação, consultar estado autoritativo quando necessário e aplicar um único movimento de crédito à compra confirmada.

#### Scenario: Notificação duplicada ou fora de ordem

- **WHEN** Mercado Pago envia notificações duplicadas ou atrasadas
- **THEN** a inbox e a compra convergem sem duplicar crédito nem regredir confirmação final

#### Scenario: ID alfanumérico na assinatura do webhook

- **WHEN** uma notificação contém `data.id` alfanumérico de Order e assinatura válida pelo manifest bruto do SDK oficial
- **THEN** o sistema SHALL preservar a caixa do ID ao conferir o HMAC; a variante legada em minúsculas somente pode ser aceita com seu próprio HMAC válido, mantendo autenticação e compatibilidade dos callbacks existentes

#### Scenario: Pagamento pendente, cancelado ou recusado

- **WHEN** a consulta autoritativa não confirma pagamento
- **THEN** não há crédito disponível e a ordem permanece em estado financeiro correspondente

### Requirement: Reversões financeiras auditáveis

O sistema SHALL permitir consulta/reconciliação da ordem e registrar confirmação tardia, reembolso e chargeback com eventos financeiros próprios. A relação entre tenant, compra, pagamento e ledger SHALL ser preservada. O sistema MUST NOT criar débito automático pelos créditos consumidos após reembolso ou chargeback.

#### Scenario: Downgrade com histórico de compras

- **WHEN** um downgrade de schema removeria compras de créditos ou seus eventos financeiros
- **THEN** a migration recusa a operação antes de remover tabelas ou registros

#### Scenario: Webhook não chega

- **WHEN** pagamento enviado não recebe callback
- **THEN** consulta do backend pode reconciliar a ordem sem reenviar uma cobrança nova

#### Scenario: Chargeback com créditos já usados

- **WHEN** o provedor confirma chargeback após parte do saldo ter sido consumida
- **THEN** o evento financeiro é preservado e nenhum débito automático é lançado pelos créditos consumidos

### Requirement: Bloqueio durante revisão financeira

Reembolso total/parcial ou chargeback confirmado SHALL abrir revisão financeira e bloquear novos uploads e compras do tenant até decisão expressa do `PlatformOwner`. Somente o proprietário SHALL liberar acesso ou manter o bloqueio, com justificativa e horário auditáveis. Qualquer outra revisão pendente ou restrita SHALL manter o bloqueio ativo.

#### Scenario: Tenant com revisão financeira

- **WHEN** uma compra do tenant está em revisão financeira pendente ou restrita
- **THEN** a API recusa novas reservas de upload e novas compras, mesmo que reste saldo positivo; a interface informa o bloqueio sem substituir a autorização do servidor

#### Scenario: Resolução da revisão pelo proprietário

- **WHEN** o proprietário registra liberação ou manutenção do bloqueio com justificativa
- **THEN** o evento append-only registra resultado, ator e horário; a liberação só remove o bloqueio se não houver outra revisão pendente ou restrita do tenant

### Requirement: Validação com credenciais de teste

O checkout SHALL usar credenciais e contas de teste do Mercado Pago na validação inicial. A separação entre teste e produção MUST ser feita por credenciais e contas distintas, pois ambas usam o mesmo host da API. O sistema MUST NOT emitir pagamentos com credenciais reais sem autorização expressa e MUST NOT persistir PAN ou CVV.

#### Scenario: Credenciais de teste ausentes

- **WHEN** as credenciais e contas de teste não estão disponíveis
- **THEN** testes locais usam adapter sintético e o gate externo permanece pendente, sem fallback para credencial de produção
