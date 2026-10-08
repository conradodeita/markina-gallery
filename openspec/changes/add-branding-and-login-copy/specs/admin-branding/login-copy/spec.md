## Purpose

Permitir identidade visual e mensagens de entrada controladas pelo fotógrafo sem alterar a estrutura ou segurança da aplicação.

## ADDED Requirements

### Requirement: Configuração de marca administrativa

O sistema SHALL permitir ao fotógrafo configurar logotipo, ícone do app e favicon por área administrativa autenticada, com validação de tipo, dimensão e tamanho dos arquivos.

#### Scenario: Ativo válido

- **WHEN** o fotógrafo envia um ativo de marca válido
- **THEN** o sistema o salva e o exibe nas superfícies correspondentes com fallback seguro

### Requirement: Textos configuráveis da entrada

O sistema SHALL permitir ao fotógrafo configurar título, texto introdutório e mensagens auxiliares da tela de login, preservando os controles de autenticação e acessibilidade.

#### Scenario: Texto salvo

- **WHEN** o fotógrafo salva texto válido
- **THEN** a tela de entrada apresenta o novo conteúdo sem permitir HTML ou script arbitrário
