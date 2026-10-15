# Design

## Context

Consulte `proposal.md` e a delta spec para o problema e os critérios observáveis. Atualmente, a barra raiz contém Aparência, enquanto identidade, notificações e saída são renderizadas no mesmo cabeçalho flexível da navegação do fotógrafo.

## Goals / Non-Goals

**Goals:**
- Colocar os três controles na barra de Aparência somente nas rotas administrativas.
- Manter a faixa do menu administrativo dedicada à navegação.
- Preservar componentes, autorização e ações existentes.

**Non-Goals:**
- Alterar autenticação, comportamento das notificações ou saída.
- Mover os controles do portal de cliente ou da galeria pública.

## Decisions

- Renderizar um grupo administrativo condicional no layout raiz, guiado pela rota atual. O grupo só aparece após a API de identidade confirmar o papel `admin`, ficando na mesma faixa global de Aparência sem duplicar controles no cabeçalho nem mostrá-los nas telas de entrada.
- Remover o grupo do cabeçalho administrativo. A navegação existente continua no cabeçalho e usa seu comportamento responsivo atual.
- Reutilizar o grupo flexível já usado pelos controles, permitindo quebra de linha na barra superior em telas estreitas.

## Risks / Trade-offs

- A barra pode ocupar uma linha adicional em telas pequenas; seus controles ficam acima da navegação e não cobrem opções.
- A identidade é carregada de forma assíncrona; o grupo preserva o comportamento atual de ocultá-la quando a consulta autenticada falha.
