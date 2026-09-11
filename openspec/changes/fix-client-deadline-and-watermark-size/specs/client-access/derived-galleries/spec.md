## ADDED Requirements

### Requirement: Prazo herdado e contextual da seleção privada

O sistema SHALL transformar o prazo padrão configurado na Galeria pública em uma data absoluta autoritativa quando criar a galeria privada da cliente. Enquanto essa data estiver vigente, a interface SHALL exibi-la à cliente quando houver fotos selecionadas ainda editáveis e sem comunicação de pagamento; a expiração SHALL bloquear novas alterações e finalização, sem remover o histórico de pedidos ou fotos compradas.

#### Scenario: Cliente possui seleção ainda não comunicada

- **WHEN** a cliente possui fotos no carrinho de uma galeria privada, o pagamento desse conjunto ainda não foi comunicado e o prazo está vigente
- **THEN** a galeria e a biblioteca exibem a data limite devolvida pelo backend junto da próxima ação de seleção

#### Scenario: Pagamento do conjunto foi comunicado

- **WHEN** a cliente comunica o pagamento e o conjunto deixa de ser uma seleção editável
- **THEN** a interface apresenta o estado do pedido sem tratar a data como prazo para editar aquele conjunto congelado

#### Scenario: Prazo herdado expira

- **WHEN** a data autoritativa herdada da Galeria pública é atingida
- **THEN** o sistema bloqueia novas seleções e checkout, preserva a consulta do histórico permitido e oferece o fluxo existente de solicitação de reabertura

