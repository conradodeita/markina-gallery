## Purpose

Disponibilizar ao fotógrafo um cadastro global de clientes independente das galerias, com identidade única por telefone e exclusão segura do estado exclusivamente operacional.

## ADDED Requirements

### Requirement: Diretório global independente de galerias

O sistema SHALL fornecer ao fotógrafo autenticado um diretório de clientes acessível pela navegação administrativa mesmo quando não existir nenhuma Galeria pública. A listagem SHALL permitir busca por nome ou telefone, cadastro e abertura da edição, e SHALL manter visíveis clientes vinculadas, indicando seus vínculos em vez de removê-las dos resultados.

#### Scenario: Administração sem galeria

- **WHEN** o fotógrafo abre Clientes sem possuir galerias
- **THEN** o sistema apresenta o estado vazio do diretório e permite cadastrar, buscar e editar clientes sem exigir a criação prévia de galeria

#### Scenario: Cliente já vinculada

- **WHEN** uma cliente retornada pela busca já possui um ou mais vínculos
- **THEN** o cadastro permanece visível com seus estados e quantidades agregadas, sem duplicar a identidade

### Requirement: Edição preserva a identidade canônica

O sistema SHALL permitir alterar o nome da cliente e trocar seu telefone na mesma identidade. O telefone SHALL ser normalizado, verificado pelo fluxo vigente e permanecer único; a alteração SHALL preservar vínculos e histórico e SHALL NOT criar uma segunda cliente.

#### Scenario: Troca de telefone

- **WHEN** o fotógrafo confirma o novo telefone com a verificação exigida
- **THEN** o sistema atualiza a identidade existente, invalida acessos dependentes do número anterior conforme a política e mantém galerias e histórico associados ao mesmo UUID

#### Scenario: Telefone já utilizado

- **WHEN** o novo telefone normalizado já pertence a outra cliente
- **THEN** o sistema recusa a alteração sem mesclar cadastros nem revelar dados adicionais da outra identidade

### Requirement: Exclusão distingue operação de histórico comercial

O sistema SHALL classificar o inventário da cliente em dependências operacionais removíveis e histórico comercial protegido. Vínculos, sessões, convites, seleções sem pedido, favoritos, comentários, visualizações, buscas faciais transitórias e galerias privadas sem histórico SHALL NOT, isoladamente, impedir a exclusão; pedidos, pagamentos, entregas e seus snapshots SHALL impedir a exclusão definitiva.

#### Scenario: Cliente sintética com privada sem compra

- **WHEN** o fotógrafo confirma a exclusão de uma cliente que possui somente vínculos e uma galeria privada sem histórico comercial
- **THEN** o sistema remove atomicamente a identidade e seu grafo operacional, encerra ou preserva a privada conforme existam outros membros e confirma a exclusão imediatamente na interface

#### Scenario: Cliente com histórico comercial

- **WHEN** o inventário encontra pedido, pagamento ou entrega preservável
- **THEN** o sistema bloqueia a exclusão definitiva, apresenta as categorias que justificam o bloqueio e orienta editar o telefone ou administrar os vínculos sem apagar o histórico

### Requirement: Exclusão isolada, idempotente e auditável

A exclusão SHALL exigir confirmação explícita e chave idempotente, repetir o mesmo resultado para a mesma operação e ocorrer sob controle de concorrência. Ela SHALL preservar Galerias públicas, JPEGs, configurações, outras clientes, membros restantes e histórico de terceiros; a auditoria SHALL registrar UUID, ator, resultado e contagens, sem nome, telefone ou conteúdo comercial.

#### Scenario: Privada compartilhada

- **WHEN** a cliente excluída é membro de uma privada que ainda possui outra cliente
- **THEN** o sistema remove somente a associação e as interações individuais da cliente alvo, mantendo a privada e os demais membros inalterados

#### Scenario: Repetição da confirmação

- **WHEN** a mesma chave idempotente é reenviada após uma exclusão concluída
- **THEN** o sistema retorna o resultado anterior sem executar novamente efeitos ou auditorias materiais
