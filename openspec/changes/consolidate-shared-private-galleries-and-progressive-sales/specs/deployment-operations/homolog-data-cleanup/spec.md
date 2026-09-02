## ADDED Requirements

### Requirement: Limpeza controlada de dados sintéticos em homologação
O sistema SHALL fornecer uma operação administrativa fora da API pública para inventariar e limpar galerias, fotos, contatos e dependências sintéticas exclusivamente em homologação. A operação SHALL exigir ambiente, projeto, confirmação literal e autorização do Environment, SHALL criar backup lógico antes da execução e SHALL preservar administrador, configurações, pareamento WhatsApp e recursos externos ou de terceiros.

#### Scenario: Inventário sem PII
- **WHEN** o operador executa o modo `inventory` no projeto `markina-gallery`
- **THEN** a operação retorna somente contagens de banco e mídia, topologia e estado dos containers, sem nomes, telefones, secrets ou conteúdo de mensagens

#### Scenario: Ambiente ou confirmação inválidos
- **WHEN** a operação destrutiva não está em `APP_ENV=homolog|homologation`, fora de `/opt/markina-gallery` ou sem a confirmação literal esperada
- **THEN** ela falha antes de alterar banco, Redis, mídia ou serviços

#### Scenario: Limpeza autorizada
- **WHEN** o proprietário autoriza a limpeza, o inventário é conhecido e o commit aprovado carrega a sinalização exata da operação
- **THEN** a automação cria backup lógico, interrompe somente API/worker da Markina, remove o grafo de galerias e clientes, limpa filas e mídia exclusivas, reinicia os dois serviços e comprova contagens zeradas e saúde
