## Purpose

Permitir que cada cliente revise, retome e compre apenas as fotos privadas que lhe foram destinadas a partir de um acervo-mãe do evento.

> **Supersession:** este delta registra o comportamento inicialmente entregue. Configuração independente, persistência obrigatória e navegação exclusivamente privada foram supersedidas por `improve-gallery-and-client-data-lifecycle`; a implementação futura SHALL seguir a herança da Galeria pública, a derivação sob demanda e o histórico comercial independente.

## ADDED Requirements

### Requirement: Galeria derivada privada por cliente

O sistema SHALL permitir ao fotógrafo criar uma galeria derivada para um cliente autorizado, referenciando fotos de um acervo-mãe sem duplicar os arquivos ou conceder acesso à lista completa do acervo.

#### Scenario: Criação pelo fotógrafo

- **WHEN** o fotógrafo escolhe fotos de um acervo-mãe e um cliente autorizado
- **THEN** o sistema cria uma galeria derivada privada contendo somente essas referências e a inclui na biblioteca daquele cliente

#### Scenario: Acesso do cliente

- **WHEN** o cliente autenticado abre sua galeria derivada
- **THEN** o sistema exibe somente as fotos atribuídas a ele e não revela outras fotos, pessoas ou a estrutura do acervo-mãe

### Requirement: Configuração independente da galeria derivada

O sistema SHALL permitir ao fotógrafo definir, por galeria derivada, prazo de seleção, mensagem personalizada, estado de acesso e permissões de favoritos e comentários.

#### Scenario: Prazo e mensagem próprios

- **WHEN** o fotógrafo salva prazo e mensagem em uma galeria derivada
- **THEN** somente o cliente daquela galeria recebe esses valores ao acessá-la ou em mensagens autorizadas

#### Scenario: Acesso vencido

- **WHEN** o prazo de nova seleção expira
- **THEN** o sistema bloqueia novas interações de seleção, preserva o histórico de compras e não altera galerias derivadas de outros clientes

### Requirement: Persistência do histórico privado

O sistema SHALL manter a galeria derivada e seu histórico de seleções e compras acessíveis ao cliente autorizado conforme as regras de acesso, mesmo que ele conclua a compra posteriormente.

#### Scenario: Retomada posterior

- **WHEN** o cliente retorna após interromper a revisão
- **THEN** o sistema restaura suas fotos atribuídas, seleções permitidas e histórico de compras sem exigir nova criação da galeria derivada
