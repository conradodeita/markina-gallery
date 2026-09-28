# Design

## Context

`ParentGallery.access_mode` e sua constraint aceitam três valores. `GalleryCreate`/`GalleryUpdate` em `backend/app/main.py` aceitam os mesmos três; `apply_public_gallery_access` trata `collective_protected` como pendência e `require_public_gallery_browsing` nega navegação mesmo com atribuição de pasta. O editor envia `access_mode` junto de outros campos. A política facial automática em `backend/app/facial/policy.py` não depende desse seletor; a busca da cliente passa pela autorização da galeria. Homologação foi limpa no workflow 36353174348, mas essa evidência não autoriza presumir ausência de registros legados em outros ambientes.

## Goals / Non-Goals

**Goals:** reduzir opções operacionais sem ampliar acesso implicitamente; manter o backend como autoridade; separar modo de entrada de audiência da pasta; suportar seleção negociada fora do sistema e exibir a mensagem configurada na revisão da cliente.

**Non-Goals:** remover dados ou constraint legada, migrar galerias em massa, alterar OTP/convites, ativar biometria, criar uma nova política facial, registrar valores negociados externamente, criar notificações financeiras fictícias ou novos eventos de WhatsApp/push.

## Decisions

### 1. Validação de escrita restrita, leitura compatível

Restringir as entradas administrativas de criação e alteração explícita a `standard|invite_only`. Manter o valor legado na constraint/modelo e nas guardas de autorização. Alternativa rejeitada: trocar automaticamente para `invite_only`, pois vínculos ativos e pastas comuns poderiam se tornar navegáveis onde antes tudo era negado.

### 2. Salvamento não converte registro legado

O editor deve informar o modo legado fora das duas opções operacionais e deixar a escolha de substituição vazia até ação explícita. Ao salvar outro campo sem essa escolha, omitir `access_mode` do PATCH. A atualização parcial do backend já admite campo ausente; testes devem provar preservação no banco. A escolha de substituição informa o efeito antes do salvamento e não promove cadastros pendentes. Não remover a guarda legada como código morto.

### 3. Textos orientados à operação

Padrão: “Quem recebe o link válido e confirma o código no WhatsApp pode entrar, sem cadastro prévio pelo fotógrafo.” Somente convite individual: “Só entram clientes vinculadas pelo fotógrafo ou autorizadas por convite individual. Encaminhar o link geral não dá acesso a outra pessoa.” Nota comum: “Nos dois modos, cada cliente vê as pastas comuns e somente as exclusivas atribuídas a ela. Seleções e compras continuam individuais.” Manter a observação de que nenhuma prévia é liberada antes de login/autorização.

### 4. Documentação substitutiva

Atualizar as referências operacionais no mandato, roadmap e `openspec/config.yaml`; `collective_protected` passa a ser apenas compatibilidade legada bloqueada. Manter as exigências de privacidade de eventos coletivos e os gates faciais existentes. Changes antigas não devem reintroduzir o terceiro modo ao serem retomadas; registrar a substituição no escopo afetado.

### 5. Cobrança configurável e compatível

Adicionar flag persistida `payment_required` com padrão verdadeiro para galerias existentes e novas. Na etapa 2, apresentar `Pagamento obrigatório?`. Quando marcado, validar valor fixo maior que zero; preservar precificação progressiva e exigir valores positivos nas faixas aplicáveis. Não converter preço zero legado em seleção sem cobrança: configuração incompatível exige revisão explícita antes de nova finalização paga, sem modificar pedidos antigos. Quando desmarcado, preservar preços administrativos configurados, mas não exigir PIX nem configuração de preços para finalizar e não expor preços/totais nas superfícies da cliente para aquela seleção.

### 6. Finalização sem cobrança e snapshot independente

O carrinho atual prepara PIX automaticamente e congela pedidos ao informar pagamento. Criar finalização autenticada e idempotente para seleções sem cobrança, validando vínculo, fotos autorizadas, prazo e revisão atual. Congelar itens e modo de cobrança no pedido, com estado distinto `Seleção finalizada` e pagamento não obrigatório; não simular pagamento confirmado. Registrar a seleção no painel do fotógrafo, dentro de Acervo da cliente, e no histórico Compras. Reutilizar o grid administrativo com limites de largura para nomes longos e o formulário existente de entrega; exportar TXT/CSV por pedido congelado em endpoint administrativo autenticado. Não emitir `payment_reported`/`payment_confirmed` nem contabilizar receita. Preservar exportação TXT/CSV e permitir entrega posterior pelo link existente, usando uma guarda central baseada no snapshot finalizado ou pagamento efetivamente confirmado; aplicar essa guarda também às prévias históricas e à notificação existente de entrega. Alterar a flag da galeria não muda pedidos congelados. A finalização descarta somente eventual rascunho pago editável daquela seleção, sem comunicação financeira; revisões PIX anteriores ficam obsoletas. A mesma política explícita de retenção de mídia histórica se aplica às seleções finalizadas, contando o prazo a partir do congelamento, sem executar limpeza de dados reais nesta change. Fotos adicionais elegíveis seguem em seleção distinta dentro do prazo; a finalização repetida não duplica itens/pedidos.

Carrinhos mistos separam as ações de seleção sem cobrança e pagamento obrigatório. O total e o agrupamento PIX incluem somente itens com cobrança; finalizar a seleção não informa pagamento nem modifica o grupo pago. A revisão deve incluir modo de cobrança no fingerprint, rejeitando confirmação obsoleta após alteração administrativa. Sem cobrança, ocultar também preços/totais em Coleção, Galerias e Compras, não apenas o botão do carrinho. Identificar o modo como negociação externa, sem chamar as fotos de gratuitas.

### 7. Mensagem comercial por galeria na revisão

Investigação: `ParentGallery.sales_message` é salvo, `_synchronize_order` copia para `sales_message_snapshot`, e `_fingerprint` do checkout inclui o texto. Entretanto `unified_checkout.cart_payload` não entrega a mensagem nos grupos e `frontend/app/library/cart/page.tsx` não a renderiza. Exibir a mensagem não vazia junto ao grupo correspondente na revisão, tanto paga quanto sem cobrança, com quebras de linha e como texto simples, sem HTML executável. Preservar snapshot de pedidos já congelados. Mudança de mensagem deve invalidar revisão obsoleta quando ela integrar o fingerprint; não mostrar texto de galeria sem autorização.

## Risks / Trade-offs

- [Exposição acidental de galeria protegida] → sem migration/conversão automática; teste de PATCH sem modo e de escolha explícita sem promover pendentes.
- [Integração antiga envia terceiro valor] → rejeição de validação documentada; nenhuma escrita ocorre.
- [Texto de Padrão sugere acesso anônimo] → explicar link válido, OTP e público autorizado; testar prévia sem sessão negada.
- [Compatibilidade mantém um valor técnico antigo] → compromisso deliberado para preservar dados e segurança; remoção definitiva exige inventário e change separada.
- [Seleção sem cobrança tratada como venda] → estado e snapshot próprios; testes de receita, entrega, histórico, notificações e carrinho misto.
- [Mudança de configuração altera pedido anterior] → congelar modo no pedido e revalidar revisão antes da finalização.
- [PIX ausente bloqueia negociação externa] → fluxo sem cobrança independente de configuração PIX e precificação.

## Migration Plan

1. Integrar a base documental do PR #107 sem misturar seus commits na implementação.
2. Validar/revisar esta proposta; implementar backend, editor e documentação com testes direcionados de acesso, cobrança, finalização e mensagem comercial.
3. Validar migration aditiva em banco isolado, preservando pedidos legados; executar regressão de autenticação/comércio/entrega, frontend, lint/typecheck/build e OpenSpec; revisar diff sem secrets/dados.
4. PR/CI e homologação pelo fluxo autorizado, precedidos de inventário e plano de impacto zero. Não criar galerias de teste no servidor sem nova necessidade explícita. Após pedidos sem cobrança existirem, rollback para código sem suporte a esse estado exige avaliação de compatibilidade; não executar downgrade destrutivo. O downgrade técnico só aceita bancos sem galerias no modo externo nem pedidos com snapshot externo, preservando a reversibilidade de testes vazios e recusando perda de configuração/histórico.
