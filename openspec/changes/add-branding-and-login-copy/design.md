## Context

A marca é configurável de modo controlado; veja `proposal.md`.

## Goals / Non-Goals

**Goals:** configurações simples, seguras e acessíveis para identidade e copy.

**Non-Goals:** editor livre de HTML/CSS, múltiplos templates ou alteração das regras de autenticação.

## Decisions

Ativos serão validados no servidor e textos serão texto simples com limites de tamanho. A tela terá valores padrão caso a configuração esteja ausente ou inválida.

## Risks / Trade-offs

- [Ativo malformado] → validação de MIME, dimensão e limite de tamanho.
- [Texto prejudicial] → sem HTML e com preview administrativo.
