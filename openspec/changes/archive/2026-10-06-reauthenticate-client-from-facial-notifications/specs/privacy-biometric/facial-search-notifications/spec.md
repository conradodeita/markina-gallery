# Spec Delta

## Purpose

Define os avisos de conclusão da busca facial e a retomada autenticada do resultado pelo próprio cliente, sem transportar resultado biométrico, PII ou token de convite no link.

## ADDED Requirements

### Requirement: Link da notificação recupera a autenticação da galeria

Notificação de busca facial SHALL levar à entrada de cliente com retorno interno à galeria correspondente e MUST NOT incluir token de convite, telefone, imagem ou resultado facial. O ID de galeria SHALL ser apenas contexto e SHALL NOT autorizar acesso.

#### Scenario: Cliente abre o aviso sem sessão

- **WHEN** o cliente abre a notificação em navegador sem sessão válida
- **THEN** a tela apresenta a entrada de cliente para nome e telefone, preserva o destino interno da galeria e solicita OTP conforme o vínculo já existente

#### Scenario: Cliente abre o aviso com sessão válida

- **WHEN** o cliente abre a notificação com sessão válida e vínculo ativo
- **THEN** o sistema abre a galeria autorizada diretamente sem exigir novo OTP

### Requirement: Resultado facial é retomado após autenticação

Após reautenticação OTP contextual bem-sucedida, a Galeria pública SHALL carregar somente a busca facial mais recente ainda válida daquele cliente e daquela galeria, usando as verificações de autorização existentes.

#### Scenario: Resultado concluído disponível

- **WHEN** o cliente autentica novamente pela notificação e existe resultado facial válido para ele nessa galeria
- **THEN** a interface apresenta esse resultado junto à galeria, sem incluir resultado ou identidade inferida no link ou na mensagem

#### Scenario: Sem resultado vigente

- **WHEN** o cliente autentica pela notificação e não existe resultado vigente para essa combinação de cliente e galeria
- **THEN** a interface abre a galeria sem revelar buscas de outros clientes nem criar uma nova busca automaticamente
