## ADDED Requirements

### Requirement: Release pontual de pagamentos preserva produção existente
O release da melhoria de situações financeiras SHALL preservar os comportamentos da versão de produção `71be3b29659143293351968e15fb4886c2d72bf0`, integrar o delta aprovado de pagamentos por PR validado e atualizar somente API/web, admitindo recarga do nginx da Markina para resolução do upstream. O release SHALL NOT executar migrations, atualizar workers, modificar configurações ou dados nem alterar recursos de terceiros.

#### Scenario: Candidato anterior ao código implantado
- **WHEN** a main não contém correções presentes na versão instalada
- **THEN** o executor reconcilia a candidata, valida o resultado e não publica uma versão que remova essas correções

#### Scenario: Publicação aprovada
- **WHEN** inventário, SHA, imagens de recuperação, domínio, portas, escopo e possível interrupção são conferidos e aprovados pelo proprietário
- **THEN** o executor preserva as imagens existentes, constrói API/web, recria somente esses serviços sem dependências e verifica saúde e acesso HTTPS

#### Scenario: Configuração ou estado divergente
- **WHEN** revisão de banco, manifesto Compose, hashes de configuração, imagens ou checkout diferem do inventário aprovado
- **THEN** a publicação para antes de trocar containers e exige reavaliação do inventário

#### Scenario: Recuperação necessária
- **WHEN** o release falha e a recuperação das imagens anteriores foi explicitamente aprovada
- **THEN** o executor restaura somente API/web e checkout anterior, recarrega o nginx da Markina e verifica saúde, sem tocar banco ou recursos de terceiros
