## Context

Veja `proposal.md` — Why — e os delta specs desta change. A página `/library` dispara `/api/library` e `/api/library/purchases` em um único `Promise.all` e só renderiza quando ambas terminam; assim, o histórico mais pesado bloqueia jornadas que já poderiam ser usadas. A mesma página guarda as fotos de um pedido em estado local e entrega o conjunto a `ProtectedPhotoViewer`, cujo fluxo principal mostra uma foto por vez. O link de ação usa `.primary` dentro de `.admin-shell`, mas a regra mais específica `.admin-shell a` pode aplicar ao texto a mesma cor do fundo e torná-lo visualmente vazio.

Na galeria privada, a resposta já fornece `commercial_state`, porém os filtros e contadores usam `purchase_state` e não oferecem as categorias `awaiting_payment` e `payment_reported`. `GalleryPresentation` sempre monta o hero, inclusive quando essa superfície não passa capa, produzindo `Capa ainda não definida`. Pedidos são blocos independentes no DOM, mas reutilizam o mesmo tratamento visual e pouco espaçamento. A change anterior já estabeleceu projeção em lote, carrinho persistente e pedidos congelados; esta change não pode alterar essas autoridades.

## Goals / Non-Goals

**Goals:**

- reduzir o tempo até a primeira jornada útil sem esconder atraso ou falha do histórico;
- verificar por contagem de consultas que o ganho no frontend não mascara N+1 no backend;
- apresentar o conjunto completo de cada pedido sem fundir registros comerciais;
- usar uma classificação comercial única nos filtros, marcadores e acompanhamento;
- resolver capa e contraste por extensões compartilhadas, com padrão compatível para os demais consumidores;
- manter a validação focada nos componentes, rotas e projeções tocados.

**Non-Goals:**

- mudar criação, congelamento, confirmação, correção ou cancelamento de pedidos;
- combinar pedidos, carrinhos ou preços entre galerias;
- remover capas da Galeria pública, da configuração administrativa ou de outros usos editoriais;
- alterar `purchase_state` no backend, migração, mídia, reconhecimento facial ou integrações;
- transformar a biblioteca em renderização integral de todas as fotos antes de interação da cliente.

## Decisions

### 1. Jornadas e histórico terão ciclos de carregamento independentes

A página manterá estados separados para jornadas e histórico. A consulta essencial começará imediatamente e, ao concluir, liberará o cabeçalho e os cards; a consulta de compras será iniciada sem bloquear essa renderização e terá loading, erro e nova tentativa próprios. Um `loading.tsx` no segmento fornecerá feedback durante a transição de rota, e os links oficiais para `/library` manterão prefetch do App Router.

As duas respostas continuam orientadas pelo backend e nenhuma será armazenada em `localStorage`. A primeira consulta não será ampliada com todas as miniaturas dos pedidos, porque isso aumentaria o payload crítico. Antes de alterar o FastAPI, um teste instrumentado medirá quantidade de consultas com várias galerias/pedidos; otimização backend será aplicada somente se a medição revelar crescimento por entidade ou consulta duplicada relevante.

Alternativa descartada: consolidar todo o histórico e suas miniaturas em `/api/library`. Isso reduz uma requisição, mas aumenta o tempo, a memória e o payload necessários para a primeira jornada útil.

### 2. `Ver fotos` expandirá uma grade dentro do próprio pedido

Cada card de pedido conservará seu cabeçalho, valor e estado e terá um controle `Ver fotos (n)` com `aria-expanded`/`aria-controls`. Ao abrir, renderizará somente os itens daquele pedido numa grade dedicada. CSS explícito usará quatro colunas em desktop e duas no mobile, preservando proporção e `object-fit: contain`. A miniatura abrirá um diálogo de uma foto para ampliação; controles sequenciais poderão existir somente dentro dessa ampliação e não como única forma de conhecer o conjunto.

Alternativa descartada: reunir todos os itens num grid global. Isso apaga a fronteira financeira entre pedidos complementares e galerias diferentes.

### 3. A ação principal usará o componente de link do design system

O link primário da biblioteca migrará para o componente compartilhado de ação, que controla variante, contraste, foco e nome acessível sem depender da cascata genérica de `.admin-shell a`. Um teste de regressão verificará texto visível e classe/variante efetiva.

Alternativa descartada: aumentar a especificidade de um seletor global. Isso corrigiria um caso por disputa de CSS e poderia modificar links administrativos não relacionados.

### 4. A classificação dos filtros será `commercial_state`

A página derivará contagens e visibilidade da enumeração já devolvida pelo backend: `selected`, `awaiting_payment`, `payment_reported` e `purchased`; `all` permanece o total autorizado e fotos `available` aparecem nele. Os rótulos serão `Todas`, `Carrinho`, `Aguardando pagamento`, `Pagamento informado` e `Compradas`. `purchase_state` continuará disponível para informação secundária, mas não comandará os filtros comerciais.

Alternativa descartada: acrescentar os dois estados ausentes à lista atual de `Novas`/`Vistas`. Isso mantém no mesmo nível categorias ortogonais — navegação e compra — e continua difícil explicar por que os subtotais não compõem o total.

### 5. O hero compartilhado será opcional e ligado por padrão

`GalleryPresentation` receberá uma opção explícita para omitir o hero. O padrão continuará ligado, preservando Galeria pública, prévias e administração. Apenas a galeria privada comercial passará a opção desligada; cabeçalho, proteção, pastas, grade e visualizador não serão duplicados.

Alternativa descartada: ocultar `.gallery-presentation-hero-empty` por CSS somente nessa rota. O conteúdo permaneceria no DOM, ocuparia estrutura semântica desnecessária e não resolveria o acoplamento do componente.

### 6. Estado do pedido controlará classe visual, nunca a regra financeira

A apresentação mapeará o estado autorizado do pedido para variantes semânticas de classe ou atributo. Espaçamento maior separará os artigos; borda, fundo e indicador auxiliar distinguirão aguardando, informado, confirmado e cancelado. Texto e `StatusBadge` continuarão presentes para que a distinção não dependa apenas de cor. Nenhuma ação mudará de disponibilidade por causa do CSS.

Alternativa descartada: ordenar ou agrupar pedidos em colunas separadas por estado. Em mobile isso afasta as fotos do contexto e dificulta acompanhar pedidos complementares cronologicamente.

## Risks / Trade-offs

- [Histórico aparecer depois das jornadas causar mudança de layout] → reservar cabeçalho/estado local do histórico e inserir cards abaixo das jornadas sem deslocar a ação ativa.
- [Duas consultas independentes gerarem atualização após unmount] → cancelar requisições com `AbortController` no cleanup e ignorar cancelamentos como erro.
- [Muitas miniaturas abertas num pedido aumentarem uso de memória] → renderizar a grade somente após expansão, manter `loading="lazy"` e usar prévias protegidas existentes.
- [Nova opção do hero afetar outros consumidores] → valor padrão `true` e teste do comportamento ligado/desligado no componente compartilhado.
- [Cores de estado perderem contraste ou dependerem só de cor] → tokens com contraste, borda/indicador e rótulo textual cobertos por teste acessível.
- [Medição de tempo ser instável em CI] → usar contagem de consultas como contrato automatizado e registrar tempo observado apenas como evidência diagnóstica, sem threshold frágil de relógio.

## Migration Plan

1. Adicionar testes frontend inicialmente falhos para carregamento progressivo, ação visível, grade por pedido, filtros comerciais, hero opcional e variantes de pedido.
2. Instrumentar testes backend direcionados de `/library` e `/library/purchases` com várias galerias/pedidos; corrigir somente N+1 ou duplicação reproduzida.
3. Implementar estados de carregamento independentes, ação compartilhada e grade expansível na biblioteca.
4. Implementar hero opcional, filtros por `commercial_state` e variantes visuais na galeria privada.
5. Executar somente testes direcionados, ESLint dos arquivos tocados, typecheck, validação OpenSpec estrita e `git diff --check`; ampliar a validação apenas se uma falha indicar risco compartilhado.
6. Preparar inventário zero-impact e solicitar autorização específica antes de qualquer deploy. Não há migration nem transformação de dados.

Rollback restaura o frontend anterior sem modificar pedidos, seleções, fotos ou contratos persistidos. Eventual otimização backend deverá permanecer compatível com as respostas atuais e poderá ser revertida independentemente.
