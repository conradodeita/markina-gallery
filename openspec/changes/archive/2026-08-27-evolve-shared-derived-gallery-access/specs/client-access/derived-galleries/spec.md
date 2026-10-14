## MODIFIED Requirements

### Requirement: Persistência do histórico privado

O sistema SHALL manter uma biblioteca visual para cada responsável autorizado, onde ele retoma galerias derivadas, suas próprias seleções e seu próprio histórico sem acesso ao acervo-mãe ou aos dados de outros responsáveis. Uma mesma galeria derivada poderá ter vários responsáveis autorizados e todos verão somente o conjunto de fotos atribuído à galeria.

#### Scenario: Biblioteca vazia

- **WHEN** a cliente autenticada não possui galeria derivada ativa
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

#### Scenario: Responsáveis compartilham galeria com históricos independentes

- **WHEN** mãe e pai possuem acesso ativo à mesma galeria derivada
- **THEN** ambos veem as fotos autorizadas da galeria, mas cada um vê somente suas próprias seleções, favoritos, comentários, pedidos, pagamentos e entregas

## ADDED Requirements

### Requirement: Vínculos individuais de acesso à galeria derivada

O sistema SHALL preservar uma cliente proprietária na galeria derivada e tratar o acesso de cada responsável adicional como vínculo independente, com status e auditoria próprios. A proprietária e os responsáveis adicionais acessam somente seus próprios dados de interação e comércio.

#### Scenario: Fotógrafo vincula segundo responsável

- **WHEN** o fotógrafo vincula um responsável já cadastrado à galeria derivada
- **THEN** o responsável passa a acessar a galeria após validar nome e telefone por OTP, sem alterar a proprietária nem receber seleções ou pedidos de outra pessoa

#### Scenario: Fotógrafo bloqueia somente um responsável

- **WHEN** o fotógrafo bloqueia o acesso de um responsável a uma galeria compartilhada
- **THEN** esse responsável perde acesso às fotos da galeria, enquanto os demais responsáveis ativos continuam acessando suas próprias informações

#### Scenario: Acesso pré-existente é preservado na migração

- **WHEN** uma galeria derivada existente é migrada para o modelo de vínculos individuais
- **THEN** seu cliente previamente associado permanece autorizado e nenhum outro cliente recebe acesso automaticamente

### Requirement: Expiração e reativação sem perda de histórico

O sistema SHALL impedir novas seleções após o prazo da galeria expirar, sem apagar pedidos, pagamentos, compras ou entregas, e SHALL permitir ao fotógrafo definir novo prazo para reativar a seleção.

#### Scenario: Galeria expirada aparece como congelada

- **WHEN** o prazo de seleção de uma galeria termina
- **THEN** ela deixa de aceitar novas seleções e aparece como congelada na operação administrativa, preservando o histórico de cada responsável

#### Scenario: Fotógrafo reativa prazo

- **WHEN** o fotógrafo define um novo prazo para uma galeria congelada
- **THEN** as novas seleções voltam a ser permitidas aos responsáveis com acesso ativo, sem alterar pedidos e compras anteriores
