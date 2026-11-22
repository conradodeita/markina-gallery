# Spec Delta

## MODIFIED Requirements

### Requirement: Cadastro completo antes de nova compra de créditos

O servidor SHALL exigir e-mail verificado e perfil operacional completo, incluindo CPF e endereço, antes de preparar ou criar uma nova compra de créditos. O aceite dos Termos MUST NOT ser pré-requisito para compra. PIX recebedor e WhatsApp do fotógrafo MUST NOT ser exigidos para comprar créditos; os controles financeiros existentes continuam aplicáveis. Compras já iniciadas SHALL continuar elegíveis à confirmação/reconciliação autoritativa.

#### Scenario: Conta exploratória tenta comprar
- **WHEN** fotógrafo sem e-mail verificado ou sem perfil operacional completo tenta preparar ou criar diretamente uma nova compra
- **THEN** o servidor recusa a compra e informa a pendência em Configurações, sem criar Order

#### Scenario: Compra antes do aceite dos Termos
- **WHEN** fotógrafo com e-mail verificado, perfil completo e controles financeiros válidos inicia compra sem aceite vigente ou sem documento disponível
- **THEN** a compra pode prosseguir sem registrar aceite implícito e sem liberar upload

#### Scenario: Pagamento já iniciado
- **WHEN** webhook ou reconciliação confirma uma Order previamente criada
- **THEN** o movimento financeiro segue o contrato existente sem depender do estado atual do onboarding ou do aceite
