# Spec Delta

## ADDED Requirements

### Requirement: Cobrança obrigatória com recebimento disponível

O sistema SHALL exigir ao menos um meio utilizável da conta autenticada ao salvar a etapa 2 com `Pagamento obrigatório?` marcado ou disponibilizar essa galeria às clientes. PIX válido SHALL ser padrão; cartão SHALL contar somente com configuração pronta e habilitação individual. Ausência de meios SHALL rejeitar a operação sem alteração parcial, com orientação para Configurações. Criar rascunho SHALL continuar possível antes de configurar recebimento.

#### Scenario: Cobrança obrigatória sem recebimento
- **WHEN** o fotógrafo salva a etapa 2 paga sem PIX utilizável nem cartão habilitado/pronto
- **THEN** UI e API recusam a configuração e orientam configurar recebimento ou desmarcar cobrança obrigatória
- **AND** preço, modo e demais campos anteriores permanecem inalterados

#### Scenario: Recebimento pertence a outro fotógrafo
- **WHEN** somente outra conta possui PIX ou cartão disponível
- **THEN** a configuração paga e a disponibilização não usam esse meio para satisfazer a exigência da conta atual

#### Scenario: Reativação de galeria já publicada
- **WHEN** o fotógrafo tenta reativar uma galeria paga com pastas já liberadas e sem meio utilizável
- **THEN** a API recusa a reativação sem alterar o estado inativo, até configurar recebimento

#### Scenario: PIX e cartão disponíveis
- **WHEN** a cliente inicia revisão paga de uma conta com ambos os meios utilizáveis
- **THEN** PIX inicia selecionado e cartão pode ser escolhido explicitamente

#### Scenario: Cartão utilizável sem PIX cadastrado
- **WHEN** a conta nunca configurou PIX e possui cartão pronto e habilitado
- **THEN** cartão satisfaz a exigência de pelo menos um meio e sua preparação não depende de um PIX inexistente

### Requirement: Preservação do último meio de galeria paga

Alterações de configuração SHALL revalidar no servidor se deixariam galeria disponibilizada com cobrança obrigatória sem qualquer meio utilizável. Nesse caso SHALL ser recusadas sem alteração parcial e orientar configurar outro meio ou mudar explicitamente a jornada das galerias afetadas. Pedidos e links já emitidos SHALL manter snapshots e reservas conforme o contrato existente.

#### Scenario: Desligar cartão com PIX disponível
- **WHEN** o fotógrafo desliga a oferta de cartão e conserva PIX utilizável
- **THEN** novos pedidos dessa conta continuam pagando por PIX e outras contas permanecem independentes

#### Scenario: Retirar último meio utilizável
- **WHEN** alteração InfinitePay retiraria o único meio de uma galeria paga disponibilizada
- **THEN** a alteração é rejeitada e a configuração anterior permanece

### Requirement: Jornada sem cobrança independente do recebimento

Com `Pagamento obrigatório?` desmarcado, o sistema SHALL permitir salvar regras e finalizar seleção sem configurar PIX/cartão. A revisão SHALL apresentar `Finalizar seleção` e ocultar meios, preços e totais daquele grupo. Finalização SHALL preservar identidade, autorização, revisão e idempotência existentes, sem gerar cobrança, receita ou aviso financeiro. Carrinhos mistos SHALL cobrar somente grupos pagos.

#### Scenario: Galeria somente para seleção
- **WHEN** a cliente revisa somente fotos de galerias sem cobrança e a conta não tem recebimento configurado
- **THEN** pode finalizar a seleção sem etapa PIX ou InfinitePay e sem preço ou total

#### Scenario: Carrinho com dois modos
- **WHEN** a cliente reúne uma galeria paga e outra sem cobrança
- **THEN** o grupo sem cobrança mantém finalização independente, mesmo se o grupo pago tiver erro de configuração

\n