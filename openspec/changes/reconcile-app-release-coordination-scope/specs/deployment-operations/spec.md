# Spec Delta

## ADDED Requirements

### Requirement: O escopo API/web admite somente os arquivos exatos de coordenação de release já revisados
O verificador de release API/web SHALL permitir, além dos runtimes e artefatos previamente enumerados, somente os arquivos `scripts/deploy-prod-lock.sh`, `scripts/deploy-prod-web.sh`, `scripts/test_deploy_prod_web.sh` e `scripts/test_deploy_prod_web_policy.py` como delta operacional desta integração. A allowlist SHALL NOT aceitar outros caminhos operacionais por diretório ou padrão aproximado.

#### Scenario: Delta inclui a coordenação de release aprovada
- **WHEN** o diff desde o baseline contém um ou mais dos quatro caminhos exatos de coordenação e nenhum caminho fora da allowlist
- **THEN** o verificador mantém elegível somente o escopo API/web com os hashes de runtime já aprovados

#### Scenario: Delta inclui operação não listada
- **WHEN** o diff inclui outro script de deploy ou um arquivo semelhante não enumerado
- **THEN** o verificador recusa o candidato antes do inventário remoto

#### Scenario: Allowlist operacional é reconciliada
- **WHEN** os quatro caminhos exatos são permitidos
- **THEN** o baseline, os hashes de runtime, a revisão do banco e os gates de inventário e aprovação permanecem inalterados
