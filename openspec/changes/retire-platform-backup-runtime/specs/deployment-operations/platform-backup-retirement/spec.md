## ADDED Requirements

### Requirement: Retirada delimitada do backup global descontinuado

A retirada SHALL eliminar da operação a configuração, as entradas de execução, credenciais dedicadas e cópias verificadas da tentativa descontinuada. MUST preservar o banco, os dados de clientes, a mídia, integrações compartilhadas e seus mecanismos de recuperação.

#### Scenario: Console do proprietário após publicação

- **WHEN** o proprietário consulta o armazenamento externo
- **THEN** o Console SHALL manter a conexão e os registros do Drive e apresentar somente o estado dos recursos que continuam no seu escopo
- **AND** a API MUST deixar de oferecer a seleção e a autorização da pasta global descontinuada

#### Scenario: Retirada de credencial ou cópia

- **WHEN** uma credencial, chave ou cópia tem origem e uso exclusivo comprovados
- **THEN** sua retirada SHALL usar o canal autorizado para o ambiente e ser confirmada por evidência sem segredo ou dado pessoal
- **AND** uma dependência ainda ativa ou uma identidade incerta MUST bloquear a remoção do item correspondente
