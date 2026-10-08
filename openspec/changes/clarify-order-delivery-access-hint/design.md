# Design

## Context

Consulte `proposal.md` e a delta spec para motivação e comportamento observável. O card de Compras já alterna entre um link ativo e um botão desabilitado conforme a disponibilidade do álbum.

## Goals / Non-Goals

**Goals:**
- Mostrar a orientação apenas no estado em que o álbum está indisponível.

**Non-Goals:**
- Alterar regras de pagamento, disponibilização, notificações ou navegação do álbum.

## Decisions

- Renderizar o texto junto ao botão desabilitado existente. A condição de renderização acompanha o mesmo estado que escolhe esse botão, evitando divergência entre dica e disponibilidade.
- Manter a orientação como texto estático e acessível, sem torná-la clicável enquanto não houver URL de entrega.

## Risks / Trade-offs

- A expressão “quando o fotógrafo liberar o álbum” evita prometer acesso automático ao fim da edição, pois a disponibilidade também depende da configuração da entrega.
