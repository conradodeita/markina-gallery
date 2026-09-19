# Continuidade — 2026-09-19

## Estado e escopo

- Branch: `codex/fix-purchase-previews-payment-shortcuts-and-expiry`, base `655b6489e609173fbda3873fab9f4362b46a0a60` (`origin/develop` no início).
- Implementação local autorizada e concluída: tarefas 1.1–3.3 e 4.1–4.2 (10/12). Publicação/deploy e aceite humano remoto permanecem pendentes em 4.3–4.4.
- Sem migration, edição de secrets/ambiente, alteração de infraestrutura, transação financeira real, envio de WhatsApp/push real ou acesso a mídia real nesta validação.
- Não foi executada a suíte completa. Mudanças locais anteriores de `configurable-push-and-whatsapp-notifications`, `persist-branding-assets-across-deploys` e `.codex-tmp/` ficam preservadas e fora do commit desta change.

## Implementação

1. `PurchasePreview` normaliza somente rotas protegidas de histórico/galeria do cliente sob `/api`, uma única vez. Biblioteca usa o componente na miniatura e ampliação; falha/nulo mantém nome, quantidade e espaço da foto com mensagem curta. Não aceita rota administrativa, original ou URL externa.
2. `build_commercial_projections` inclui pedidos comunicados e capacidades compartilhadas com Vendas e pagamentos, agrupados pelas consultas existentes. Pendências primeiro; dentro de cada grupo, pedidos mais novos primeiro. Cada compra preserva comunicação, quantidade, valor e ID próprios, sem ocultar pendências anteriores. A comunicação mais recente é usada por pedido.
3. `PaymentActions` reutiliza endpoints existentes nos cards da pública, editor, privada e Vendas e pagamentos. Confirmação explícita identifica cliente/galeria/pedido/valor; bloqueia duplo clique, trata conflito HTTP 409 e resposta idempotente 200 divergente, preserva chave de correção em falha incerta e revalida projeções. Correção continua silenciosa. Prévia de templates globais é carregada sob demanda e oferece atalho para Notificações.
4. `SelectionDeadline` apresenta data/hora e tempo restante, atualiza pelo relógio local a cada minuto e ao retornar à aba. Revalidação no vencimento não modifica pagamentos. Prazo efetivo vem do backend, inclusive na resposta da primeira seleção comum/facial. Não recarrega a grade após selecionar. Biblioteca agrupa revalidações concorrentes e mantém histórico independente. Admin mostra prazo nos cards e ficha; cliente vê o prazo mesmo com carrinho vazio/pagamento informado. Nenhuma data persistida foi reescrita.

## Evidências locais

### Frontend

- Última execução direcionada: `npx vitest run app/purchase-preview.test.tsx app/selection-deadline.test.tsx app/admin/payments/payment-actions.test.tsx app/admin/payments/page.test.tsx app/admin/galleries/gallery-editor.test.tsx app/library/library.test.tsx app/gallery/gallery.test.tsx app/public-galleries/public-gallery.test.tsx` → **127 testes, 8 arquivos aprovados**.
- Complemento: `npx vitest run app/admin/galleries/galleries.test.tsx` → **10 testes aprovados**. Total dos arquivos focados na versão final: **137**, em duas execuções, não uma suíte global.
- Cobrem prefixo/rotas/mídia ausente, pedidos independentes, cancelar confirmação, duplo clique, conflitos, correção e falha de rede, refresh no editor/refoco, prazos futuros/expirados/nulos/reabertos e vencimento com página aberta sem nova consulta de histórico ou mutação financeira.
- `npx tsc --noEmit` e `npm run build` aprovados. ESLint dos arquivos tocados e script de QA: sem erros; avisos de `no-img-element` em prévias autenticadas/existentes. Nenhuma supressão global de lint.

### Backend

Última execução integrada direcionada: **15 testes aprovados**, com `DATABASE_URL` somente no processo apontando para SQLite temporário exclusivo (nunca o banco local de uso nem homologação). Seletores:

```text
tests/test_payment_shortcut_projection.py
tests/test_gallery_lifecycle.py::test_client_library_uses_isolated_historical_media_after_gallery_removal
tests/test_gallery_lifecycle.py::test_client_purchase_history_starts_only_after_payment_communication
tests/test_media.py::test_protected_preview_requires_authorized_role_and_never_returns_original
tests/test_derived_galleries.py::test_real_selection_routes_keep_public_and_private_counters_in_sync_through_payment
tests/test_derived_galleries.py::test_same_client_commercial_journey_stays_isolated_across_two_galleries_and_folders
tests/test_derived_galleries.py::test_parent_gallery_clients_aggregates_commercial_precedence_in_constant_queries
tests/test_derived_galleries.py::test_private_gallery_inherits_parent_configuration_and_checkout_freezes_terms
tests/test_derived_galleries.py::test_expired_selection_and_foreign_client_interactions_are_denied
tests/test_derived_galleries.py::test_expired_gallery_rejects_checkout_of_existing_selection
tests/test_derived_galleries.py::test_expired_gallery_rejects_freezing_an_open_draft
tests/test_derived_galleries.py::test_private_media_payment_correction_and_reopening_contracts_start_missing
tests/test_notification_payments.py
tests/test_notification_delivery.py::test_channels_independent_and_claim_concurrent
```

- JPEG sintético realmente decodificado nas respostas históricas/operacionais; cliente correto autorizado, outro cliente e anônimo negados, arquivo ausente retorna 404 sem apagar compra.
- Projeção em no máximo 5 consultas, identidade/galeria isoladas, múltiplos pedidos preservados, confirmação/correção atualiza contagens corretas, datas individuais inalteradas. Expiração bloqueia alterações e checkout no backend.
- Testes existentes de canais independentes e correção silenciosa passaram com transportes simulados. Ruff dos seis arquivos Python tocados passou. Avisos de depreciação existentes de FastAPI/Starlette não impedem a execução.

### Visual e revisão

- `frontend/scripts/purchase-flow-visual-qa.cjs` executado sobre build local em `127.0.0.1:3106`, com API simulada e imagens sintéticas; nenhuma decisão real. `PLAYWRIGHT_MODULE` aponta apenas para a instalação local disponível de Playwright, sem dependência adicionada ao projeto.
- **390, 768 e 1440 px**, temas **claro e escuro**: seis combinações aprovadas. Imagem decodificada, caminho incorreto sem `/api` reproduzido/rejeitado, grid 2/4, teclado/ampliação/Escape, decisão isolada no pedido escolhido e ausência de overflow horizontal.
- Capturas em `.codex-tmp/purchase-flow-qa/`, fora do Git; inspeção visual de biblioteca mobile escura, pública desktop clara e privada mobile clara. Servidor temporário de QA encerrado após verificar seu PID/comando; nenhum outro processo foi encerrado.
- Diff relevante revisado; `git diff --check` e OpenSpec estrito aprovados. Não houve relaxamento de autorização de mídia ou dos gates de pagamento.

## Próximos passos e limites

1. Obter autorização aplicável para publicar esta change; incluir somente seus arquivos. Após push, **encerrar execução e aguardar o proprietário conferir Actions**, conforme pedido explícito. Não fazer polling, monitor automático ou automação.
2. PR/checks, merge e deploy precisam seguir os gates do repositório. Antes de deploy, apresentar inventário, portas/subdomínio e plano de impacto zero; preservar serviços terceiros, configurações e workers. Não inferir paridade/deploy a partir dos testes locais.
3. Após deploy autorizado, proprietário valida a compra reportada originalmente, os atalhos por pedido e o contador em dispositivo real. O arquivo real da captura ainda não foi inspecionado nesta change; não afirmar recuperação de mídia remota ou entrega em homologação.
4. Somente após revisão humana sincronizar specs principais e arquivar. Tarefas 4.3–4.4 permanecem abertas até evidência correspondente.
