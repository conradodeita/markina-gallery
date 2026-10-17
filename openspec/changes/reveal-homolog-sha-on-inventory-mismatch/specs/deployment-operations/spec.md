## ADDED Requirements

### Requirement: Diagnóstico de revisão divergente no inventário de homologação

O script de inventário somente leitura SHALL informar o SHA esperado e o SHA observado quando o checkout fixo de homologação não corresponder à revisão esperada. SHALL encerrar a execução com erro e SHALL evitar qualquer consulta Compose, container, banco, volume ou endpoint público enquanto houver divergência.

#### Scenario: SHA do checkout diverge do esperado

- **WHEN** o operador informa um SHA válido que difere de `git rev-parse HEAD` em `/opt/markina-gallery`
- **THEN** o inventário SHALL exibir os dois SHAs e informar que nenhuma consulta foi executada
- **AND** SHALL encerrar com erro antes de invocar Docker ou consultar endpoints

#### Scenario: SHA do checkout corresponde ao esperado

- **WHEN** o SHA esperado corresponde ao `HEAD` do checkout fixo
- **THEN** o inventário SHALL manter o comportamento read-only especificado, sem adicionar ações de alteração ou implantação
