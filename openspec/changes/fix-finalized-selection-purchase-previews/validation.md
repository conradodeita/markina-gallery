# Validation

## Evidência anterior à implementação — 08/10/2026

- O proprietário relatou que os três clientes atualmente autenticados estão na conta do fotógrafo A e que as fotos aparecem ao abrir a galeria, mas não as prévias de entrada.
- Capturas fornecidas às 09:32 mostram `/library` com as duas galerias A e `Prévia indisponível`; em Compras, o pedido sem cobrança finalizado em 02/10/2026 contém DES00377.jpg e DES00380.jpg, ambas com fallback de prévia.
- Consulta PostgreSQL somente leitura, explicitamente iniciada com `SET TRANSACTION READ ONLY`, confirmou `cover_photo_id=null` nas galerias de carga A e piloto A. A biblioteca projeta capa somente mediante configuração explícita pronta, diferentemente do fallback de seleção automática da rota interna da galeria.
- Pastas de carga A: liberada/comum, 166 fotos disponíveis e 166 derivados ready para cada variante admin_preview/client_preview/thumbnail. Piloto A: duas pastas liberadas, três fotos cada, variantes ready para as seis fotos; três estados de cliente ativos sem expiração e uma atribuição de pasta exclusiva. Nenhum arquivo foi regenerado nem regra de público alterada.
- O pedido das duas fotos é canônico (sem contexto privado), sem cobrança e elegível segundo `order_fulfillable`. O serializer de Compras produz `/library/purchases/items/{item_id}/preview` para esse caso. `purchasePreviewUrl` aceita somente histórico, galeria privada e galeria pública; por isso devolve null para a rota comercial e o componente mostra o fallback sem solicitar imagem.
- Leitura agregada e sanitizada do log próprio da API desde 12:29 UTC encontrou biblioteca e Compras com HTTP 200, quatro pedidos de capa pública HTTP 200 e 501 pedidos de prévia de fotos públicas HTTP 200; nenhum pedido de rota comercial de prévia apareceu nesse recorte. As contagens não identificam cliente individual; são consistentes com a rejeição local identificada no componente, não prova adicional de autorização de todos os casos.
- Uma primeira consulta de metadados tentou ler atributo inexistente `payment_required` do pedido e foi encerrada sem escrever. Repetida com `payment_required_snapshot`, confirmou os metadados acima.

## Estado

Somente planejamento e investigação. Nenhum código alterado, teste de aplicação executado, commit, PR ou deploy nesta change. A regressão antes/depois continua pendente. A ausência de capa é independente; o proprietário solicitou posteriormente torná-la obrigatória, e essa alteração de produto deve ter change própria.

Planejamento concluído com proposal, delta spec, design e tasks. `npx.cmd --yes @fission-ai/openspec@1.14.0 validate fix-finalized-selection-purchase-previews --strict`: aprovado. O fluxo openspec-propose encerra em planejamento e requer nova instrução de aplicação após apresentação dos artefatos; nenhuma task de implementação foi marcada.

Obrigatoriedade de capa planejada separadamente em `require-gallery-cover-in-details`, após o proprietário delegar a escolha da etapa. Decisão: cobrar em Detalhes e Concluir, mantendo cadastro inicial/Ajustes/Vendas disponíveis. Essa nova exigência não faz parte da correção da URL de miniaturas em Compras.

## Aplicação autorizada em 08/10/2026

O proprietário autorizou implementar as mudanças, fazer push/merge/deploy após conclusão. Integração na branch codex/gallery-cover-client-preview-and-otp-copy sobre origin/develop af5b3a6, sem diferença de código preexistente em relação ao baseline. As mudanças serão separadas em commits; documentação local antiga de deploy/OTP continua preservada e não integra os commits novos.

Regressão antes da correção: `npm.cmd test -- app/purchase-preview.test.tsx app/library/external-selection.test.tsx` terminou com 27 aprovados e duas falhas esperadas em 25,19 s. O novo formato foi rejeitado como null e o card real de seleção finalizada mostrou o fallback em vez da imagem. Alteração de aplicação limitada à aceitação exata do caminho de item de purchases.

Validação após correção: os cinco arquivos frontend de prévia/carrinho/biblioteca/entrega/seleção externa passaram (58 testes). Backend em SQLite descartável próprio fora do repositório: confirmed_canonical_preview_survives_folder_revocation e canonical_external_selection_api_admin_export_and_history, 2 passed/23 deselected em 25,35 s. Cobertura existente comprovou item próprio após revogação da pasta, recusa de item alheio e pedido inelegível. Dois avisos FastAPI e um de ciclos FK em drop_all das fixtures antigas.

Lint frontend: aprovado, zero erros e 37 avisos existentes. Typecheck tsc --noEmit: aprovado. Build Next 16.3.2: aprovado, compilação 26,5 s e TypeScript 12,9 s. OpenSpec 1.14.0 estrito e diff-check aprovados. Escopo revisto: uma extensão exata de formato no normalizador e regressões correspondentes; nenhuma alteração de endpoint ou de autorização comercial. Entrega/CI permanece pendente até concluir os commits independentes do pacote autorizado. O proprietário autorizou também push, merge e deploy deste pacote após conclusão, condicionados ao CI e inventário apresentados.
