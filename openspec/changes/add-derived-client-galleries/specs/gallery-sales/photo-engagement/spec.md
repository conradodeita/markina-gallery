## Purpose

Definir interações privadas de seleção, favoritos e comentários para apoiar a revisão de fotos sem expor conteúdo entre clientes.

## ADDED Requirements

### Requirement: Seleção e favorito reversíveis

O sistema SHALL permitir ao cliente autorizado selecionar e favoritar fotos de sua galeria derivada quando essas ações estiverem habilitadas, bem como desfazer cada ação sem afetar outros clientes.

#### Scenario: Favoritar foto habilitada

- **WHEN** o cliente favorita uma foto em galeria com favoritos habilitados
- **THEN** o sistema registra o favorito apenas para aquele cliente e apresenta o estado atualizado na mesma galeria

#### Scenario: Desfazer interação

- **WHEN** o cliente remove uma seleção ou favorito permitido
- **THEN** o sistema remove somente a interação daquele cliente e preserva o histórico de auditoria aplicável

#### Scenario: Recurso desabilitado

- **WHEN** o fotógrafo desabilita favoritos ou comentários na galeria derivada
- **THEN** o cliente não pode criar novas interações desse tipo e as interações existentes seguem a política de visualização definida pelo fotógrafo

### Requirement: Comentários privados por foto

O sistema SHALL permitir comentários por foto somente entre o cliente que acessa a galeria derivada e o fotógrafo administrador, sem torná-los visíveis a outros clientes.

#### Scenario: Comentário do cliente

- **WHEN** o cliente autorizado comenta uma foto em galeria com comentários habilitados
- **THEN** o comentário fica visível somente para esse cliente e para o fotógrafo administrador

#### Scenario: Remoção pelo autor

- **WHEN** o cliente remove seu próprio comentário ou o fotógrafo remove um comentário daquela galeria derivada
- **THEN** o sistema deixa de exibir o comentário e registra a ação sem expor seu conteúdo a terceiros

#### Scenario: Tentativa de acesso cruzado

- **WHEN** outro cliente tenta consultar ou alterar comentário de uma galeria derivada alheia
- **THEN** o sistema nega a operação sem revelar a existência do comentário
