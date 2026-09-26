# Design

## Context

Ver proposal.md. A captura corresponde a `gallery-editor.tsx`, etapa Imagens, usando `.folder-photo-grid`. O artigo é um grid de coluna automática; o nome extenso pode definir sua largura intrínseca e alargar os filhos, incluindo o botão e a imagem a 100%. A regra global de min-width em article/div não limita a coluna interna automática. O grid externo tem mínimo fixo de 145px. A galeria cliente usa outro componente e não deve ser alterada por esta correção.

## Goals / Non-Goals

**Goals:** corrigir o dimensionamento na origem, com reprodução em navegador real e dados exclusivamente sintéticos.

**Non-Goals:** alterar proporção/enquadramento da miniatura, arquivos e nomes persistidos, rotas, dados, ações comerciais, backend ou componentes da cliente.

## Decisions

- Conter a coluna interna do card com minmax(0,1fr) e permitir quebra de palavras no nome/estado. Limitar o botão de prévia à largura disponível; adaptar o mínimo do grid externo ao espaço disponível em telas estreitas.
- Preferir exibir o nome completo em múltiplas linhas a truncá-lo, porque é identificação operacional. Não mascarar o defeito com overflow:hidden no card ou no documento.
- Usar QA com Playwright/Edge e a página real, APIs interceptadas. Reproduzir antes, confirmar depois; medir caixas de imagem, nome, botão e card, além do documento. Incluir segunda pasta, nomes curtos e longos, retrato/paisagem, celular/desktop e claro/escuro.
- Manter todos os arquivos preexistentes do workspace fora do escopo. Nenhum acesso às fotografias ou banco da homologação é necessário para reproduzir este problema de layout.

## Risks / Trade-offs

- [Nomes extensos aumentam altura da legenda] → aceitável para preservar identificação; verificar controles e grade em diferentes larguras.
- [CSS global possui regras sobrepostas] → editar somente seletores da grade afetada e validar a cascata real, sem refatorar a folha.

## Migration Plan

Sem migration ou alteração de dados. A branch desta correção pode ser enviada ao repositório sem deploy; qualquer publicação em homologação ou produção segue os gates operacionais próprios, sem reutilizar o aceite de deploy do PR #99.
