# Spec Delta

## ADDED Requirements

### Requirement: Inventário usa a origem pública configurada em homologação
O inventário manual SHALL validar a origem pública homologada contra `PUBLIC_APP_ORIGIN` do Compose e SHALL reutilizar essa origem validada nos health checks externos, sem codificar um hostname fixo.

#### Scenario: Origem esperada ausente ou inválida
- **WHEN** o workflow não recebe `HOMOLOG_PUBLIC_BASE_URL` ou a URL não é uma origem HTTPS sem credenciais, caminho, query ou fragmento
- **THEN** SHALL interromper antes da conexão SSH e dos probes públicos, sem imprimir o valor recebido

#### Scenario: Origem diferente da configuração do projeto
- **WHEN** o hostname esperado não corresponde a `PUBLIC_APP_ORIGIN` do Compose Markina
- **THEN** SHALL interromper o inventário antes de consultar serviços ou dados e SHALL identificar apenas a categoria da divergência

#### Scenario: Origem configurada corresponde ao servidor
- **WHEN** a origem HTTPS esperada corresponde à configuração pública da Markina
- **THEN** SHALL exibir somente o hostname e executar os health checks públicos nessa mesma origem, além de manter o escopo somente leitura
