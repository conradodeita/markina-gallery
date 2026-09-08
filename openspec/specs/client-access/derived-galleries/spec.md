# derived-galleries Specification

## Purpose

Definir o acesso privado da cliente às galerias derivadas, incluindo retomada de seleções, permissões e histórico sem exposição do acervo-mãe.

## Requirements

### Requirement: Persistência do histórico privado

O sistema SHALL manter uma biblioteca visual para a cliente autorizada, onde ela retoma galerias derivadas, seleções e histórico sem acesso ao acervo-mãe.

#### Scenario: Biblioteca vazia

- **WHEN** a cliente autenticada não possui galeria derivada ativa
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

### Requirement: Interface da cliente orientada pelo backend

O sistema SHALL renderizar biblioteca, permissões, prazo, interações e histórico da cliente a partir de respostas autorizadas do backend.

#### Scenario: Permissão alterada

- **WHEN** o fotógrafo altera acesso, prazo ou permissões de uma galeria derivada
- **THEN** a cliente vê o novo estado retornado pelo backend sem o frontend conceder ou preservar permissão localmente
