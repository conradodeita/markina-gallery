# Spec Delta

## MODIFIED Requirements

### Requirement: Estados operacionais claros

O sistema SHALL apresentar estados de carregamento, vazio, erro, preparação, progresso, sucesso, bloqueio e expiração nas telas administrativas e da cliente, com linguagem compreensível e ação de recuperação quando aplicável. A página Estatísticas SHALL apresentar estados distintos para ausência de vendas, seleções sem compra, dados indisponíveis e falha de consulta, sem substituir falhas ou dados não instrumentados por zero, e preservar os filtros durante a recuperação.

#### Scenario: Importação em processamento

- **WHEN** um JPEG foi aceito e seus derivados ainda estão sendo preparados
- **THEN** o fotógrafo vê o estado pendente sem receber URL do original

#### Scenario: Liberação concluída

- **WHEN** o fotógrafo conclui a liberação de uma pasta
- **THEN** a interface confirma o resultado retornado pelo backend e informa quais galerias privadas foram atualizadas

#### Scenario: Falha ao consultar estatísticas

- **WHEN** uma consulta de estatísticas falha após a autenticação administrativa
- **THEN** a interface apresenta erro recuperável e não substitui os indicadores por zeros

#### Scenario: Galeria sem prazo de seleção configurado

- **WHEN** a galeria/cliente não tem prazo de seleção persistido ou ele ainda não expirou
- **THEN** suas seleções não são classificadas como abandonadas e nenhum prazo ou valor potencial é inventado
