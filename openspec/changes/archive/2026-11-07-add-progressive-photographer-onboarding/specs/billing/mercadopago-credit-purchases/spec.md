# Spec Delta

## ADDED Requirements

### Requirement: Cadastro completo antes de nova compra de créditos

O servidor SHALL exigir perfil operacional completo e aceite vigente do fotógrafo antes de preparar ou criar uma nova compra de créditos. PIX recebedor e WhatsApp do fotógrafo MUST NOT ser exigidos para comprar créditos. Compras já iniciadas SHALL continuar elegíveis à confirmação/reconciliação autoritativa.

#### Scenario: Conta exploratória tenta comprar
- **WHEN** fotógrafo sem perfil ou aceite solicita catálogo/checkout e tenta criar Order diretamente
- **THEN** pode conhecer pacotes, mas o servidor não cria compra e informa a etapa pendente em Configurações

#### Scenario: Pagamento já iniciado
- **WHEN** webhook ou reconciliação confirma Order previamente criada
- **THEN** o movimento financeiro segue o contrato existente sem depender do estado atual do onboarding


### Requirement: Checkout de créditos pré-preenchido com perfil do fotógrafo

O checkout SHALL pré-preencher nome completo, e-mail verificado, CPF e endereço do pagador a partir do perfil do próprio tenant. A Order MUST enviar os dados efetivos em `payer.address`; ajustes na compra MUST NOT alterar o perfil contratual.

#### Scenario: Checkout pré-preenchido
- **WHEN** fotógrafo elegível prepara uma compra de créditos
- **THEN** nome, e-mail, CPF e endereço aparecem a partir do perfil; eventuais ajustes são enviados em `payer.address` somente para essa Order
