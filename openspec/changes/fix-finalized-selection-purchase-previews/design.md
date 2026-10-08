# Design

## Context

Ver `proposal.md`. O normalizador em `frontend/app/purchase-preview.tsx` aceita prévias de histórico e fotos de galerias pública/privada, mas rejeita `/library/purchases/items/{item_id}/preview`. Essa quarta rota é produzida por `client_purchases` para pedidos canônicos elegíveis sem cópia histórica e já possui autorização própria no servidor. O card substitui a URL rejeitada por `Prévia indisponível` antes de montar um elemento de imagem.

O banco de homologação confirmou que o pedido A das fotos DES00377.jpg e DES00380.jpg é canônico, sem cobrança e finalizado; ambas têm derivados prontos. A biblioteca tem problema visual independente explicado por ausência de capa configurada nas duas galerias. Evidências e limites em `validation.md`.

## Goals / Non-Goals

**Goals:** corrigir a compatibilidade entre o payload de Compras e a validação estrita do componente; preservar autenticação, origem local e proteção visual.

**Non-Goals:** alterar autorização, snapshots, estado financeiro, capa automática, orientação OTP, cache, infraestrutura ou geração/retencão de mídia. A lista de formatos permitidos no frontend não concede acesso ao item.

## Decisions

1. Incluir exatamente a rota de item de Compras na lista permitida. Não aceitar qualquer caminho sob `/library`, pois isso removeria a restrição atual de formatos. Não trocar para prévia operacional: o pedido possui autorização comercial própria que pode sobreviver à remoção de acesso à pasta.
2. Preservar o tratamento de prefixo `/api`, URLs inválidas e erro de imagem. Derivados e endpoint existentes atendem ao contrato; reprocessar fotos ou alterar permissões não corrige a rejeição local.
3. Regressão primeiro: verificar que o caminho real retornado pelo backend vira a URL API esperada, com e sem prefixo, e que o card de seleção finalizada monta a imagem. Proteger também alternativas indevidas e compatibilidade das três rotas antigas, sem mockar o normalizador.
4. Conservar o backend de autorização. Reutilizar testes existentes do endpoint de itens canônicos e da finalização sem cobrança após conferir o baseline; quaisquer falhas correlatas devem ser delimitadas antes de ampliar a correção.

## Risks / Trade-offs

- Aceitar caminhos excessivamente amplos → restringir o padrão à rota exata de prévia por item e adicionar negativas de URL externa, original, rota administrativa, traversal, query/fragment e prefixo duplicado.
- Confundir capa ausente, prévia protegida e entrega final → manter o tratamento atual das capas sem configuração; `Fotos indisponíveis` no botão de Google Photos não significa falha da miniatura e não deve ser alterado por esta correção.
- Confundir duas ou três sessões de A com ensaio A+B → manter task 8.3 pendente e retomar dois fotógrafos distintos somente após a correção e confirmação contextual.

## Migration Plan

Sem migration. Após aprovação, implementar e validar localmente, revisar diff e preparar PR focado sobre o baseline de integração vigente. Publicação exige CI verde, inventário/plano de impacto zero e autorização explícita; não reutilizar a autorização de deploy da PR #144 para esta nova change. Reversão pelo fluxo Git/deploy normal, sem alteração de dados.
