# Operações da galeria privada e Vendas e pagamentos

## Composição do acervo privado

A galeria privada combina duas origens legítimas:

1. fotos que a própria cliente seleciona na Galeria pública, mantidas automaticamente na privada pela origem `client`;
2. novos JPEGs carregados pelo fotógrafo diretamente em pastas da privada, com proprietário `derived_gallery_id` e storage key sob `private/<gallery-id>/`.

A interface administrativa não oferece catálogo, botão ou atalho para o fotógrafo incluir manualmente na privada fotos já existentes na Galeria pública. O backend também recusa criação com `photo_ids`, inclusão posterior e clonagem de referências existentes. Referências históricas são preservadas para consulta e limpeza controlada, e o fluxo automático da seleção da cliente continua ativo. Upload privado usa o mesmo pipeline de validação JPEG, derivados sem EXIF/GPS, prévia protegida e indexação facial, mas não entra no snapshot de busca pública.

## Projeção e estados comerciais

Galeria pública, ficha privada e seleção individual usam uma projeção comum por `(galeria privada, cliente)`. `Fotos no acervo privado` representa o acervo compartilhado autorizado; `Fotos selecionadas` e `Fotos compradas` permanecem individuais. Pedido pendente não conta como compra; somente itens de pedido confirmado contam. Uma correção de confirmação devolve a mesma comunicação a `pending_review`, recalcula imediatamente compras e estatísticas e registra histórico append-only sem enviar nova mensagem.

`/admin/payments` é a área canônica **Vendas e pagamentos**. Ela mostra seleções sem pedido, pedidos sem comunicação, pagamentos comunicados, confirmados, não localizados, itens por pasta, falhas de entrega e solicitações de reabertura. `/admin/purchases` permanece apenas como redirecionamento compatível.

Templates de confirmação e não localização são globais. A edição afeta decisões futuras de todas as galerias; cada confirmação salva no pedido e na outbox o conteúdo renderizado efetivamente usado. A decisão financeira é persistida antes do consumo assíncrono da outbox, portanto falha de WhatsApp não desfaz o status.

## Expiração e reabertura

Depois de `selection_expires_at`, mutações de seleção, remoção que altere carrinho aberto e checkout são recusadas pelo backend. Consultas, pedidos, pagamentos e compras continuam visíveis. A cliente vê `Solicitar novo prazo para seleção das fotos` e pode criar uma única solicitação pendente por galeria; vários membros compartilham esse pedido operacional.

O fotógrafo decide em **Vendas e pagamentos**. Aprovar exige data futura e reabre a galeria inteira para os membros ativos; recusar mantém o congelamento. O aviso ao fotógrafo usa outbox independente, pode falhar e ser reenfileirado sem perder a solicitação.

## Migration, compatibilidade e rollback

A revision `20260909_0052` é aditiva. Mídia legada permanece pública (`derived_gallery_id IS NULL`) com UUIDs, folders, storage keys e referências inalterados. A aplicação anterior pode ser restaurada mantendo as novas tabelas e colunas. Downgrade estrutural só é permitido quando não existe mídia privada, correção financeira ou solicitação de reabertura; havendo estado novo, a migration recusa o downgrade para evitar perda.

Antes de deploy: fazer backup, confirmar SHA integral e migration atual, conferir o projeto Compose `markina-gallery`, não alterar serviços de terceiros e preservar `FACIAL_PROCESSING_ENABLED=true` na homologação autorizada. Após deploy: validar healthchecks, upload privado, prévias, índice facial privado, contadores cruzados, expiração/reabertura e decisão/correção financeira. Rollback de aplicação não apaga estruturas nem arquivos novos.
