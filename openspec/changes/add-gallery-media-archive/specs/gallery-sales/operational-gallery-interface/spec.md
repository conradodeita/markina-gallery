## ADDED Requirements

### Requirement: Cartão de reabertura identifica o alcance

A área autenticada Vendas e pagamentos SHALL informar, antes da decisão, o alcance da aprovação conforme o escopo da pasta.

#### Scenario: Solicitação de pasta pública

- **WHEN** o fotógrafo consulta uma solicitação pendente vinculada a uma pasta pública
- **THEN** o cartão informa que o novo prazo valerá para todas as clientes autorizadas antes de permitir a aprovação

#### Scenario: Solicitação de pasta privada

- **WHEN** o fotógrafo consulta uma solicitação pendente vinculada a uma pasta privada
- **THEN** o cartão informa que o novo prazo valerá somente para a cliente solicitante antes de permitir a aprovação

### Requirement: Solicitação sem pasta não pode ser aprovada

A interface SHALL NOT oferecer aprovação para solicitação pendente sem identificador de pasta.

#### Scenario: Solicitação legada sem pasta

- **WHEN** o fotógrafo consulta uma solicitação pendente antiga sem `folder_id`
- **THEN** a interface não oferece aprovação, explica que é necessário solicitar novamente pela pasta desejada e mantém recusa ou reenvio de aviso quando aplicáveis

### Requirement: Escopo desconhecido não autoriza aprovação

A interface SHALL NOT presumir alcance público nem oferecer aprovação quando o escopo recebido não for reconhecido.

#### Scenario: Escopo não identificado

- **WHEN** a solicitação referencia uma pasta, mas a resposta não contém um escopo reconhecido
- **THEN** a interface não presume que o acesso será público, não oferece aprovação e orienta o fotógrafo a atualizar os dados antes de decidir
