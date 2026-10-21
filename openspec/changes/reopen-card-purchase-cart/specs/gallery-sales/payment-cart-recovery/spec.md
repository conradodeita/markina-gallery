# Spec Delta

## Purpose

Permitir que o fotógrafo reabra o carrinho de uma compra pendente de cartão, devolvendo as fotos à cliente para nova escolha de pagamento e conservando a verdade financeira do histórico anterior.

## ADDED Requirements

### Requirement: Elegibilidade restrita à ausência de resultado conclusivo
A reabertura manual SHALL atender somente compra de cartão sem retorno financeiro ou com resultado inconclusivo. Pagamento confirmado em PIX ou cartão MUST NOT ser reaberto. Falha clara prevista no contrato SHALL seguir o tratamento documentado existente; estado de não criação comprovada MUST NOT ser tratado como resultado incerto.

#### Scenario: Compra já confirmada
- **WHEN** PIX ou cartão já possui confirmação financeira válida
- **THEN** não há reabertura nem restauração de suas fotos por esta ação

#### Scenario: Falha clara de não criação
- **WHEN** o provedor confirmou não criação e a compra está em failed_before_issue
- **THEN** segue a restauração existente e não oferece recuperação excepcional da tentativa

### Requirement: Reabertura administrativa por compra
O sistema SHALL oferecer Reabrir carrinho no card da cliente em Vendas e pagamentos para compras elegíveis de cartão pendentes ou em verificação. A ação SHALL exigir administrador ativo da conta, prévia atual, motivo e reconhecimento explícito de que não encerra o checkout remoto. MUST NOT alterar genericamente o estado financeiro da cliente.

#### Scenario: Fotógrafo confirma a reabertura
- **WHEN** o fotógrafo revisa e confirma uma compra elegível da própria conta
- **THEN** a cliente pode retomar o carrinho com as fotos daquela compra
- **AND** a decisão registra compra, administrador, motivo e estado anterior

#### Scenario: Outra conta ou cliente sem autorização
- **WHEN** alguém tenta reabrir uma compra fora da conta administrativa ativa
- **THEN** a operação é recusada sem revelar dados ou alterar seleções

### Requirement: Recuperação integral da seleção
A reabertura SHALL restaurar todas as fotos elegíveis da compra sem duplicar nem remover seleções novas. O carrinho SHALL recalcular preços pelas regras atuais e permitir escolha dos meios já habilitados. Cartão desabilitado MUST NOT ser habilitado pela recuperação; compras de cartão não exigem PIX habilitado para voltar ao carrinho.

#### Scenario: Fotos novas já selecionadas
- **WHEN** a cliente selecionou outras fotos depois da tentativa anterior
- **THEN** o carrinho reúne as fotos antigas e novas e apresenta o total recalculado

#### Scenario: Escolha do meio disponível
- **WHEN** cartão e PIX estão habilitados na conta
- **THEN** a cliente pode escolher qualquer um no carrinho reaberto
- **AND** quando só um está habilitado, a recuperação preserva essa configuração

#### Scenario: Seleção inelegível ou nenhum meio disponível
- **WHEN** alguma foto não pode voltar integralmente à revisão ou não há meio de pagamento disponível
- **THEN** toda a reabertura é recusada sem efeito parcial

### Requirement: Preservação da verdade financeira
O sistema SHALL conservar compras, URLs, tentativas, pedidos e preços anteriores. A compra reaberta SHALL permanecer em exceção e os pedidos locais anteriores cancelados, sem confirmar recebimento nem declarar cancelamento remoto ou não criação. MUST NOT reaproveitar a mesma emissão para criar cobrança nova.

#### Scenario: Histórico após reabertura
- **WHEN** a recuperação é concluída
- **THEN** o fotógrafo vê que o carrinho foi reaberto e conserva o histórico antigo
- **AND** uma nova escolha de pagamento usa o fluxo normal do carrinho

#### Scenario: Cliente consulta a compra recuperada
- **WHEN** a cliente acessa a compra com recuperação auditada, inclusive a recuperação operacional anterior
- **THEN** vê Carrinho reaberto e acesso ao carrinho, sem bloqueio genérico da emissão antiga nem botão para seu checkout antigo

#### Scenario: Preparação PIX após reabertura
- **WHEN** o carrinho prepara um rascunho PIX ainda não comunicado
- **THEN** as fotos continuam como seleção em aberto e o rascunho não aparece como outra compra no painel financeiro
- **AND** uma comunicação ou confirmação real continua visível com o histórico preservado

#### Scenario: Fotógrafo consulta outras listas de pedidos
- **WHEN** o fotógrafo consulta os pedidos da galeria ou o diretório de clientes após preparar o PIX
- **THEN** o rascunho não aparece como outro pedido nem aumenta o contador comercial de pedidos
- **AND** inventário e bloqueio de exclusão continuam considerando todos os registros internos protegidos

### Requirement: Recusa de confirmação ou processamento conhecido
Reabertura MUST NOT aceitar pagamento confirmado, NSU persistido, recibo verificado ou verificação financeira em processamento, nem pedido entregue ou snapshot inconsistente. A prévia SHALL ser validada novamente na confirmação, com recusa integral se o contexto financeiro ou a seleção mudou.

#### Scenario: Pagamento confirmado depois da prévia
- **WHEN** uma confirmação autoritativa vence antes da reabertura
- **THEN** a recuperação é recusada e a confirmação permanece intacta

#### Scenario: Carrinho ou configuração muda
- **WHEN** o contexto difere da prévia aprovada pelo fotógrafo
- **THEN** o sistema solicita revisão atualizada sem liberar parcialmente fotos

### Requirement: Atomicidade e repetição segura
A reabertura SHALL ser transacional, auditada e idempotente. Prévia e falhas MUST NOT persistir liberação. Repetição da mesma decisão MUST NOT restaurar fotos já usadas em uma nova compra nem duplicar auditoria. Confirmação, emissão e reabertura concorrentes SHALL preservar estados finais e snapshots válidos.

#### Scenario: Repetição após nova compra
- **WHEN** a mesma decisão é repetida após a cliente iniciar outro pagamento
- **THEN** retorna a recuperação anterior sem repor fotos ou alterar o novo pagamento

#### Scenario: Cliente volta à aba depois da reabertura
- **WHEN** a cliente atualiza o carrinho após a reabertura administrativa
- **THEN** vê as mesmas fotos sem selecionar novamente e pode iniciar uma nova tentativa por escolha explícita
- **AND** a nova tentativa não reutiliza a chave da emissão antiga; sem recuperação, a mesma tentativa incerta conserva sua idempotência

#### Scenario: Resposta de criação chega depois da reabertura
- **WHEN** a emissão antiga retorna uma URL após a compra ter sido reaberta
- **THEN** a compra não volta a aguardando pagamento nem reserva novamente as fotos
- **AND** a resposta antiga permanece rastreável sem ser apresentada como checkout retomável

### Requirement: Compatibilidade e ausência de efeitos externos
A reabertura SHALL preservar PIX manual, receitas, entregas e compras de outras contas. MUST NOT criar ou cancelar checkout externo, alterar segredo/configuração, enviar mensagem ou confirmar pagamento. Retornos antigos SHALL continuar impedidos de confirmar automaticamente os pedidos cancelados.

#### Scenario: Evidência tardia da compra antiga
- **WHEN** a rotina financeira recebe evidência autoritativa para uma compra reaberta
- **THEN** conserva a exceção sem confirmar os pedidos cancelados ou alterar a nova compra
