## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado telas para criar cliente, acervo-mãe, registrar/importar JPEG e criar galeria derivada com fotos, prazo, mensagem e permissões. A operação SHALL permitir vincular mais de um responsável à mesma galeria derivada e administrar cada acesso individualmente.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui o fluxo administrativo com dados válidos
- **THEN** o sistema cria somente as referências privadas escolhidas e apresenta confirmação ou erro acessível

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos nem fotos fora de sua galeria derivada

#### Scenario: Vínculo administrativo de responsável

- **WHEN** o fotógrafo busca por nome ou telefone, ou cadastra um novo responsável, na ficha de uma galeria
- **THEN** o sistema cria ou atualiza somente o vínculo individual selecionado e apresenta o estado de acesso sem expor dados de outros clientes fora da área administrativa autorizada

## ADDED Requirements

### Requirement: Lista operacional de galerias

O sistema SHALL fornecer uma lista administrativa backend-driven de galerias derivadas, com busca por nome de galeria, nome do responsável ou telefone, ordenação operacional e filtros por seleção finalizada, pagamento pendente, acesso bloqueado e prazo expirado.

#### Scenario: Fotógrafo localiza galeria por responsável

- **WHEN** o fotógrafo busca o nome ou telefone de um responsável autenticado na área administrativa
- **THEN** a lista retorna somente galerias às quais ele está vinculado, com dados mínimos necessários para identificação operacional

#### Scenario: Fotógrafo consulta galerias congeladas

- **WHEN** o fotógrafo abre a aba de galerias congeladas
- **THEN** a lista mostra galerias com prazo expirado e oferece acesso à ação de reativar prazo

#### Scenario: Estado de pagamento pendente

- **WHEN** uma galeria tem seleção de um responsável que ainda não foi convertida em pagamento confirmado
- **THEN** o filtro operacional identifica a pendência sem atribuir o estado aos outros responsáveis da mesma galeria

### Requirement: Ficha administrativa e link controlado da galeria

O sistema SHALL apresentar uma ficha administrativa da galeria derivada com capa autorizada, link controlado de acesso, responsáveis vinculados e ações de bloquear, liberar, adicionar responsável e reativar prazo.

#### Scenario: Fotógrafo compartilha link com responsável vinculado

- **WHEN** o fotógrafo copia o link controlado de uma galeria
- **THEN** o link conduz à entrada da galeria, mas só concede acesso após a validação OTP do nome e telefone de um responsável com vínculo ativo

#### Scenario: Visitante não vinculado abre o link

- **WHEN** uma pessoa sem vínculo ativo abre o link controlado da galeria
- **THEN** o sistema não mostra fotos, não confirma a existência de cadastro e não revela responsáveis vinculados
