# Spec Delta

## MODIFIED Requirements

### Requirement: Árvore paginada e isolada
O sistema SHALL listar contas e clientes reais somente sob tree, com busca, filtro de atividade e paginação limitada. Clientes de uma conta SHALL aparecer somente no ramo correspondente. Clientes SHALL ser identificados pelo nome; fotógrafos, apenas pelo e-mail do único administrador com vínculo ativo. Sem identidade única, SHALL indicar e-mail indisponível. Nome de cliente e e-mail de fotógrafo SHALL ficar somente na árvore privilegiada e MUST NOT integrar métricas ou exportações.

#### Scenario: Clientes em contas diferentes
- **WHEN** existem identidades semelhantes em contas distintas
- **THEN** cada cliente permanece no ramo correto sem mesclar vínculos ou sessões

#### Scenario: Identificação do fotógrafo sem novo cadastro
- **WHEN** a conta possui um único administrador com vínculo ativo e o proprietário consulta a árvore
- **THEN** o rótulo mostra Fotógrafo seguido de seu e-mail atual, sem código como identificação visual ou campo de nome novo

#### Scenario: Identidade ausente ou ambígua
- **WHEN** a conta possui zero ou mais de um administrador com vínculo ativo
- **THEN** permanece na árvore com e-mail indisponível, sem escolher ou expor arbitrariamente outra identidade

#### Scenario: Pesquisa por e-mail e privacidade
- **WHEN** o proprietário pesquisa o e-mail de um fotógrafo na árvore e gera um relatório operacional
- **THEN** a pesquisa encontra somente as contas correspondentes e o relatório não inclui e-mail, árvore ou identificadores de negócio

