## Purpose

Centralizar o PIX manual do fotógrafo com alteração protegida e garantir que cada pedido preserve as instruções efetivas usadas no início do pagamento.

## ADDED Requirements

### Requirement: Configuração PIX global única

O sistema SHALL manter uma única configuração PIX ativa para o fotógrafo, independente de Galeria pública. A configuração SHALL aceitar CPF válido, telefone brasileiro normalizado, e-mail ou BR Code copia-e-cola válido e SHALL coletar nome e cidade do recebedor quando necessários para gerar o QR Code.

#### Scenario: Fotógrafo configura uma chave simples

- **WHEN** o fotógrafo informa uma chave válida, recebedor e cidade e conclui a confirmação de segurança
- **THEN** o sistema normaliza a chave, gera o BR Code/QR correspondente e disponibiliza a mesma configuração efetiva para as galerias

#### Scenario: Configuração inválida

- **WHEN** a chave, o BR Code ou os dados obrigatórios do recebedor são inválidos
- **THEN** o sistema recusa a alteração com orientação específica sem substituir a configuração vigente

### Requirement: Alteração PIX é ação administrativa sensível

O sistema SHALL exigir sessão administrativa válida, reautenticação e OTP enviado ao WhatsApp administrativo verificado para criar, substituir ou remover a configuração PIX. Desafios SHALL expirar, possuir limite de tentativas e ser vinculados à sessão e ao conteúdo proposto; a auditoria SHALL NOT registrar a chave, o BR Code ou o OTP.

#### Scenario: Confirmação válida

- **WHEN** o fotógrafo reautentica e confirma dentro do prazo o OTP vinculado à alteração proposta
- **THEN** o sistema grava uma nova versão global, invalida o desafio e audita somente identificadores e resultado

#### Scenario: Conteúdo trocado após o desafio

- **WHEN** a confirmação contém configuração diferente daquela vinculada ao desafio
- **THEN** o sistema recusa a operação e mantém a versão global anterior

### Requirement: Etapa Vendas consulta sem editar o PIX

A etapa 02 da Galeria pública SHALL exibir o estado resumido e a prévia segura do PIX global, sem campos para alterá-lo, e SHALL oferecer atalho para a configuração administrativa. Preço, tabela progressiva, prazo, mensagem comercial, favoritos e comentários SHALL continuar configuráveis por galeria.

#### Scenario: PIX global configurado

- **WHEN** o fotógrafo abre a etapa Vendas com uma configuração global válida
- **THEN** a interface identifica a versão efetiva e mostra o QR Code, recebedor e instruções sem duplicar a configuração na galeria

#### Scenario: PIX global ausente ou pendente de revisão

- **WHEN** não existe configuração global utilizável
- **THEN** a galeria pode salvar suas demais regras comerciais, mas a interface alerta que novos checkouts PIX permanecerão indisponíveis e oferece acesso direto à configuração

### Requirement: Checkout congela o PIX efetivo

O sistema SHALL resolver a versão PIX global vigente no início do checkout e congelar copia-e-cola, QR, recebedor e instruções no snapshot do pedido. Alterações globais posteriores SHALL NOT mudar pedidos já iniciados, pagamentos informados nem histórico.

#### Scenario: PIX alterado após pedido

- **WHEN** o fotógrafo substitui a configuração global depois que uma cliente iniciou o pagamento
- **THEN** o pedido existente continua exibindo o snapshot anterior e novos pedidos usam a nova versão

#### Scenario: Checkout sem PIX utilizável

- **WHEN** uma cliente tenta iniciar checkout enquanto a configuração global está ausente ou exige revisão
- **THEN** o backend recusa criar o pagamento com estado neutro e recuperável, preservando a seleção da cliente

### Requirement: Migração legada não escolhe valor divergente

O sistema SHALL preservar configurações PIX por galeria durante a janela de compatibilidade. Uma migration SHALL promover automaticamente apenas configurações não vazias que sejam canonicamente idênticas; zero configurações resultará em estado não configurado e múltiplas configurações divergentes resultarão em revisão obrigatória pelo fotógrafo.

#### Scenario: Configurações legadas iguais

- **WHEN** todas as galerias configuradas possuem o mesmo PIX canônico
- **THEN** a migration cria uma única versão global equivalente sem alterar snapshots de pedidos

#### Scenario: Configurações legadas divergentes

- **WHEN** a migration encontra dois ou mais valores canônicos diferentes
- **THEN** o sistema não elege nenhum deles, marca a configuração como pendente e exige escolha explícita antes de novos checkouts
