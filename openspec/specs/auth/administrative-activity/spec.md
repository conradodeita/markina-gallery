# administrative-activity Specification

## Purpose

Definir a autorização exclusiva do proprietário, concessões administrativas independentes e sinais limitados de atividade autenticada para a árvore de fotógrafos e clientes.

## Requirements

### Requirement: Autorizações administrativas independentes
O sistema SHALL exigir concessões explícitas para metrics, tree, incidents e export, além da sessão administrativa e vínculo ativos. A migration MUST NOT conceder acesso. A permissão do card de capacidade MUST NOT ampliar acesso implicitamente.

#### Scenario: Concessão não substitui sessão válida
- **WHEN** a sessão ou o vínculo administrativo deixa de ser válido
- **THEN** o backend recusa os dados mesmo havendo concessões ativas

### Requirement: Propriedade única por identidade permanente
Dados operacionais SHALL ser exclusivos da conta verificada do proprietário, vinculada por UUID em registro único. E-mail SHALL servir somente para identificação inicial. O backend MUST negar outras contas mesmo com grants, revalidar propriedade antes/depois de consultar e excluir a identidade de métricas, relatórios e frontend.

#### Scenario: Identificação inicial autorizada
- **WHEN** o operador identifica a conta atualmente associada a conradodeita@gmail.com para indicação inicial explicitamente autorizada
- **THEN** o UUID dessa conta é persistido como proprietário único, sem tornar seu e-mail uma regra fixa de acesso

#### Scenario: Proprietário altera seu e-mail
- **WHEN** a mesma conta proprietária troca e verifica o novo e-mail
- **THEN** mantém a propriedade pelo UUID, e nenhuma conta que passe a usar o e-mail anterior recebe acesso

#### Scenario: Outro administrador com concessão
- **WHEN** uma conta diferente da conta verificada do proprietário possui grant novo ou installation_operator
- **THEN** capabilities não expõem acesso e rotas de dados/exportação retornam negação, sem consultar dados operacionais

#### Scenario: Operador sem nova concessão
- **WHEN** um operador antigo consulta árvore ou relatório sem a concessão específica
- **THEN** o backend nega o acesso e não retorna dados globais

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

### Requirement: Atividade autenticada e limitada
O sistema SHALL aceitar sinal sem payload somente de sessão válida e interação visível, com limite de frequência, retenção curta e parâmetros configuráveis. Ativo agora SHALL exigir sinal recente; sessão válida isolada MUST NOT ser apresentada como atividade.

#### Scenario: Sessão sem sinal
- **WHEN** a sessão continua válida mas nenhum sinal de atividade foi observado
- **THEN** o estado é sessão válida ou desconhecido conforme cobertura, nunca ativo agora

#### Scenario: Revogação e aba oculta
- **WHEN** a sessão expira ou é revogada, ou a página fica oculta
- **THEN** o backend recusa o sinal inválido e o frontend não gera sinais contínuos na aba oculta

### Requirement: Cor de atividade fundamentada na árvore
A identificação dos fotógrafos e dos clientes SHALL ser verde em active e vermelha em inactive, conforme sinais/sessões revalidados já existentes. recent, valid_session e unknown SHALL permanecer neutros. O estado textual MUST permanecer visível; a cor MUST NOT ser a única informação nem transformar sessão válida em atividade ou dado antigo em offline. As cores SHALL ser legíveis nos temas claro/escuro. Clientes MUST permanecer no ramo do fotógrafo correspondente, sem ampliar acesso ou coleta.

#### Scenario: Atividade e ausência de sessão
- **WHEN** a árvore recebe active com evidência atual ou inactive sem sessão válida
- **THEN** a identificação exibe respectivamente verde ou vermelho junto ao estado textual existente

#### Scenario: Sessão ociosa ou dados ausentes
- **WHEN** a árvore recebe recent, valid_session ou unknown
- **THEN** a identificação permanece neutra, com texto que distingue atividade anterior, sessão válida e ausência de evidência

#### Scenario: Cor dos clientes no ramo autorizado
- **WHEN** o proprietário expande um fotógrafo e recebe clientes do tenant_id desse ramo
- **THEN** cada cliente recebe a cor e o texto do seu próprio estado, seguindo os mesmos critérios dos fotógrafos, sem misturar sessões entre contas
