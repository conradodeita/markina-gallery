## Purpose

Organizar a revisão manual de pagamentos e o acompanhamento das mensagens transacionais por cliente, permitindo localizar pendências e agir sem interpretar uma sequência desestruturada de eventos.

## ADDED Requirements

### Requirement: Painel de pagamentos agrupado por cliente

O sistema SHALL apresentar comunicações de pagamento, pedidos relacionados e entregas de mensagens agrupados por cliente, com resumo de totais e paginação ou limite explícito. Cada card SHALL identificar cliente, Galeria pública ou privada histórica, pedido, valor, situação financeira, prazo relevante e estado das mensagens sem expor dados bancários desnecessários.

#### Scenario: Cliente possui mais de um pedido

- **WHEN** uma cliente possui múltiplas comunicações ou pedidos no resultado
- **THEN** o painel agrupa seus itens sob a mesma identidade e preserva ações e estados individuais de cada pedido

#### Scenario: Galeria operacional foi removida

- **WHEN** o pedido pertence a galeria já removida
- **THEN** o painel usa snapshots comerciais, identifica “Galeria removida” e mantém a decisão e o histórico acessíveis

### Requirement: Estados visuais inequívocos

O sistema SHALL usar cards e badges com texto e contraste, além de cor, para distinguir `aguardando pagamento`, `pagamento comunicado`, `confirmado`, `não localizado`, `prazo expirado` e falha de mensagem. A cor SHALL NOT ser a única forma de comunicação do estado.

#### Scenario: Pagamento aguarda revisão

- **WHEN** a cliente comunicou pagamento e ainda não houve decisão
- **THEN** o card apresenta destaque de atenção, texto “Aguardando revisão” e as ações manuais permitidas

#### Scenario: Mensagem falhou

- **WHEN** a notificação ao fotógrafo ou à cliente alcança falha retomável
- **THEN** o card identifica qual mensagem falhou, mostra tentativas sanitizadas e oferece reenvio somente quando autorizado pelo backend

#### Scenario: Pagamento confirmado

- **WHEN** o fotógrafo confirma a comunicação
- **THEN** o card apresenta estado verde acompanhado do texto “Pagamento confirmado” e preserva a decisão original

### Requirement: Filtros operacionais recolhíveis

O sistema SHALL oferecer uma área de filtros que possa ser aberta sem competir com a lista principal. Os filtros SHALL permitir combinar busca por cliente, Galeria pública, período, situação financeira e estado de entrega de mensagem; o backend SHALL aplicar os filtros e devolver contagens coerentes com o resultado.

#### Scenario: Fotógrafo abre filtros

- **WHEN** o fotógrafo aciona “Filtros”
- **THEN** a interface revela os controles, anuncia seu estado e preserva os cards fora da área de edição

#### Scenario: Filtros combinados

- **WHEN** o fotógrafo filtra uma cliente, pagamento pendente e mensagem falha
- **THEN** o backend retorna somente itens que atendem a todos os critérios e o painel mostra os filtros ativos com ação para limpar

#### Scenario: Nenhum resultado

- **WHEN** a combinação não encontra pagamento
- **THEN** o painel mostra estado vazio específico e permite remover os filtros sem perder o restante da navegação

### Requirement: Decisão e mensageria permanecem auditáveis

O sistema SHALL preservar a primeira decisão manual e a idempotência das notificações existentes. Reorganizar o painel SHALL NOT confirmar pagamento por visualização, reprocessar mensagem automaticamente fora da política nem permitir que o frontend calcule autorização.

#### Scenario: Fotógrafo decide uma comunicação

- **WHEN** o fotógrafo confirma ou recusa uma comunicação pendente pelo card
- **THEN** o backend registra a decisão uma única vez, atualiza o card e enfileira somente a mensagem prevista pela regra vigente

#### Scenario: Ação repetida

- **WHEN** o botão é acionado novamente ou a resposta chega depois de atualização concorrente
- **THEN** o painel representa o estado preservado pelo backend sem duplicar decisão ou notificação
