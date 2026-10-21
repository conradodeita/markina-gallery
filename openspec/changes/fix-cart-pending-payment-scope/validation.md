# Validação e continuidade — 21/10/2026

## Estado e causa delimitada

Base: main `5446cf4d7328ef6283ebfab50b5d1976d561fc8d`, após merge do PR #260. Branch: `codex/fix-cart-pending-payment-scope`. PR #261 e PR #262 permanecem fora desta correção.

O cliente informou que nenhuma das tentativas problemáticas abriu o gateway. A consulta anterior somente de leitura encontrou `e2194ce5` em verification_required/transport_unknown e `11f18369` em verification_required/http_422, ambas de 5 centavos e sem URL persistida. Não foi recuperado o corpo da resposta 422. Ausência de redirecionamento não comprova ausência de checkout criado no provedor; HTTP 422 isolado também não demonstra valor mínimo. A confirmação do pedido d5115043 pertence a checkout criado antes do release e não valida a criação de novos links com o contrato atual.

A causa reproduzida nesta change é a projeção indiscriminada da última compra pendente no carrinho de fotos novas. Duas regressões falharam antes da correção por devolver a compra anterior em card_payment. A seleção é removida ao reservar o pedido, e `_checkout_material` já impede reutilizar suas fotos congeladas. A projeção agora correlaciona snapshots por foto, cliente e tenant; compras independentes ficam em acompanhamento separado. A regra financeira existente permanece obrigatória no backend.

## Evidência local

- Antes da correção: duas regressões falharam (tentativa unknown/accepted e foto nova); teste de foto reservada passou.
- Após a correção inicial: três regressões SQLite aprovadas, 23 desmarcadas, em 35,76 s. Posteriormente foi acrescentada uma asserção de acompanhamento de várias pendências; ela integra a repetição PostgreSQL abaixo.
- Interface: carrinho e Compras, 34 testes aprovados. O teste novo confere total atual R$ 14,00 separado da pendência de R$ 0,05, alternância PIX/cartão e ausência de emissão de cartão ao alternar.
- TypeScript sem emissão: aprovado. ESLint dos dois arquivos alterados: zero erros, dois avisos preexistentes (cleanup de ref e imagem). Build de produção Next.js: aprovado.
- Ruff e OpenSpec estrito da change: aprovados. Diff sem erros de whitespace.
- Primeira rodada PostgreSQL: 41 aprovados e 10 erros de setup por esgotamento do tmpfs de 512 MiB do banco descartável; não houve falha de asserção. O container temporário encerrou e foi removido automaticamente. Repetição com tmpfs de 2 GiB e WAL limitado: **67 aprovados**, seis avisos preexistentes, em 375,15 s, nos arquivos test_provider_checkout.py, test_unified_checkout.py e test_tenant_commerce.py. Inclui a asserção final de várias pendências, idempotência, concorrência e comércio entre tenants.

Todos os testes usam dados e provedor sintéticos. Nenhuma chamada de criação/consulta de pagamento real foi executada por esta correção. A UI autenticada publicada não foi validada visualmente: o navegador local está desabilitado nas configurações da ferramenta.

## Revisão proporcional

O campo card_payment conserva formato e comportamento quando a pendência corresponde à seleção ou quando não há seleção. pending_card_payments é aditivo; a interface o trata como opcional. A extração local pending_payload evita duplicar a projeção pública. Não foi identificado código obsoleto cuja remoção fosse necessária e segura no escopo; não houve limpeza geral nem mudança de locks, reserva, snapshots, autenticação, adaptador, secrets ou schema.

## Limites e continuação

Esta correção não aumenta o valor de uma compra congelada, não converte suas fotos para PIX e não resolve a origem do HTTP 422. Fotos novas podem compor compra independente; fotos da compra incerta continuam reservadas até reconciliação financeira suficiente e autorização expressa do proprietário. Não cancelar, liberar, reemitir ou alterar e2194ce5/11f18369 com base nesta change.

Para esclarecer as tentativas antigas, o titular precisa obter da InfinitePay a situação do checkout e pagamento pelos identificadores de pedido/compra, horário UTC, conta recebedora e valor; uma declaração apenas de que o navegador não abriu não basta. Não solicitar nem registrar API Key em chat ou Git. Uma recuperação concreta requer evidência de ausência de checkout ativo e de pagamento em andamento/confirmado, ou conciliação da transação encontrada.

Publicação exigiria API e web, sem migration, workers ou alteração de credenciais. O manifesto restrito do release anterior não autoriza automaticamente os novos blobs de unified_checkout.py e cart/page.tsx. Preparar autorização específica e gates oficiais antes de merge/publicação; rollback futuro por identidades das imagens atuais de API/web, sem desfazer pagamentos ou restaurar banco automaticamente. CI final e revisão humana continuam pendentes até haver evidência registrada no PR. Nenhum deploy desta correção foi executado.
