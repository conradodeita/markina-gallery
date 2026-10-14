# Spec Delta

## MODIFIED Requirements

### Requirement: Alteração PIX é ação administrativa sensível

O sistema SHALL exigir sessão administrativa válida, reautenticação e OTP enviado ao WhatsApp administrativo verificado para criar ou substituir a configuração PIX da própria conta. Desafios SHALL expirar, possuir limite de tentativas e ser vinculados à sessão e ao conteúdo proposto; a auditoria SHALL NOT registrar a chave, o BR Code ou o OTP. A interface SHALL oferecer somente criação/substituição e a API SHALL recusar remoção, inclusive por desafio anterior ainda pendente.

#### Scenario: Confirmação válida
- **WHEN** o fotógrafo reautentica e confirma dentro do prazo o OTP vinculado à alteração proposta
- **THEN** o sistema grava uma nova versão da própria conta, invalida o desafio e audita somente identificadores e resultado

#### Scenario: Conteúdo trocado após o desafio
- **WHEN** a confirmação contém configuração diferente daquela vinculada ao desafio
- **THEN** o sistema recusa a operação e mantém a versão global anterior

#### Scenario: Tentativa de remoção
- **WHEN** uma chamada direta ou desafio legado tenta remover PIX já configurado
- **THEN** a API recusa a remoção sem substituir o estado vigente e orienta usar substituição protegida

#### Scenario: Substituição ainda não confirmada
- **WHEN** o fotógrafo inicia a substituição e cancela, erra o código ou deixa o desafio expirar
- **THEN** o PIX vigente continua disponível para novos pedidos e snapshots anteriores permanecem preservados

### Requirement: Etapa Vendas consulta sem editar o PIX

A etapa 02 da Galeria pública SHALL exibir o estado resumido e a prévia segura do PIX da conta, sem campos para alterá-lo, e SHALL oferecer atalho para Configurações. Preço, tabela progressiva, prazo, mensagem comercial, favoritos e comentários SHALL continuar configuráveis por galeria. Com cobrança obrigatória, salvar/avançar SHALL exigir pelo menos um meio utilizável da conta; sem cobrança, ausência de PIX/cartão SHALL NOT impedir salvar.

#### Scenario: PIX global configurado
- **WHEN** o fotógrafo abre a etapa Vendas com uma configuração global válida
- **THEN** a interface identifica a versão efetiva e mostra o QR Code, recebedor e instruções sem duplicar a configuração na galeria

#### Scenario: PIX global ausente ou pendente de revisão
- **WHEN** não existe PIX utilizável e o fotógrafo salva a etapa comercial
- **THEN** cobrança obrigatória exige cartão pronto/habilitado ou configuração de PIX antes de avançar, enquanto seleção sem cobrança pode ser salva
- **AND** a interface oferece acesso direto à configuração quando recebimento é necessário
