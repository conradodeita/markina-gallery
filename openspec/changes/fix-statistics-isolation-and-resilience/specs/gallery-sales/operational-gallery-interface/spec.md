# Spec Delta

## MODIFIED Requirements

### Requirement: Estados operacionais claros

O sistema SHALL apresentar estados de carregamento, vazio, erro, preparação, progresso, sucesso, bloqueio e expiração nas telas administrativas e da cliente, com linguagem compreensível e ação de recuperação quando aplicável. Consultas administrativas de estatísticas SHALL distinguir erro de dados vazios e SHALL manter os filtros durante a recuperação.

#### Scenario: Importação em processamento

- **WHEN** um JPEG foi aceito e seus derivados ainda estão sendo preparados
- **THEN** o fotógrafo vê o estado pendente sem receber URL do original

#### Scenario: Liberação concluída

- **WHEN** o fotógrafo conclui a liberação de uma pasta
- **THEN** a interface confirma o resultado retornado pelo backend e informa quais galerias privadas foram atualizadas

#### Scenario: Consulta administrativa falha

- **WHEN** uma consulta de estatísticas falha após a autenticação administrativa
- **THEN** a interface apresenta erro recuperável e não substitui os indicadores por zeros
