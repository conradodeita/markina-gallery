# Proposal

## Why

Na tela do fotógrafo, a identidade da sessão, o controle de notificações e o botão Sair ocupam espaço na mesma faixa do menu principal e podem comprimir ou cobrir opções de navegação. Esses controles devem ficar na faixa superior, junto a Aparência, deixando a navegação administrativa livre.

## What Changes

- Mover os três controles da sessão autenticada do cabeçalho administrativo para a barra superior compartilhada com Aparência.
- Preservar as ações, o conteúdo, os rótulos e a disponibilidade dos controles da sessão.
- Manter a navegação principal em sua própria faixa e responsiva, sem sobreposição dos controles da sessão.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `auth`: definir a posição dos controles da sessão do fotógrafo separada da navegação administrativa.

## Impact

Afeta o layout raiz, o layout administrativo, os estilos da barra superior e testes de estrutura/responsividade. Sem alterações em API, autenticação, sessão, notificações ou backend.
