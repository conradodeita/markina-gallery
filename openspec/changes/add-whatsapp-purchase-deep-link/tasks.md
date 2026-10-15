# Tasks

## 1. Reconciliação de dependências e propriedade comercial

- [x] 1.1 Reconciliar origem/head e changes integradas, registrar a branch limpa `feature/add-whatsapp-purchase-deep-link`, a cadeia atual, dependências de isolamento e o checkout original preservado em `validation.md`. Evidência: worktree limpo criado a partir de `origin/develop` em `92366f5`; piloto integrado contém propriedade por tenant, cadastro independente e FKs compostas; checkout original permaneceu sem alterações desta implementação.
- [x] 1.2a Adicionar hostname canônico HTTPS único por tenant e migration aditiva sobre a cabeça integrada; testar constraints e migration no SQLite de teste, sem duplicar propriedade cliente/pedido já existente nem configurar hostname real. Evidência: migration `20261014_0081` aplica/reverte no banco SQLite isolado e os testes cobrem unicidade e validação do hostname.
- [x] 1.2b Validar migration e constraints em PostgreSQL descartável. Evidência: instância PostgreSQL 16 isolada e temporária, banco sintético, migration aplicada de `20261014_0080` para `20261014_0081`; unicidade/check, rejeição de host repetido/inválido e atualização exata do default preservando template customizado passaram. Container e volume temporário foram removidos.

## 2. Resolução do tenant, sessão e retorno OTP

- [x] 2.1 Resolver tenant somente por hostname canônico registrado para rotas de autenticação/links de cliente; testar hostname válido, desconhecido, repetido, inativo e cabeçalho encaminhado adulterado, confirmando falha fechada sem dados de outro tenant. Evidência: `tests/test_tenant_hosts.py`.
- [x] 2.2 Permitir OTP de reautenticação somente para cliente já cadastrado no tenant resolvido, vincular challenge e sessão ao mesmo tenant e manter cookie host-only seguro; testar mesmo telefone com cadastros independentes A/B, sessão de B em A e resposta neutra sem enumeração cruzada. Evidência: `test_purchase_link_reauthentication_is_host_and_client_scoped`; OTP sintético usa sandbox, sem transporte real.
- [x] 2.3 Preservar no fluxo web somente destino interno de Compras com UUID e tenant do desafio; testar acesso direto sem sessão, retorno pós-OTP para pedido próprio e fallback neutro para destino externo, malformado, de outro tenant ou de outra cliente. Evidência: testes direcionados de auth e `test_purchase_return_falls_back_for_order_from_another_tenant`.

## 3. Compras e autorização do pedido

- [x] 3.1 Confirmar e cobrir por regressão o escopo existente dos endpoints/projeções de Compras por sessão, cliente e tenant, incluindo pedidos agrupados, previews e link externo do álbum; não duplicar filtros/constraints do piloto. Evidência: revisão dos endpoints integrados e teste que um pedido de outro tenant cai no destino neutro.
- [x] 3.2 Fazer a tela abrir/posicionar o pedido indicado após carregar Compras e voltar ao login no mesmo hostname quando não houver sessão; testar sessão válida, OTP, erro neutro para pedido não autorizado e atualização sem perder o contexto. Evidência: testes frontend de `session-recovery`, boundary e auth-entry.

## 4. Link WhatsApp de fotos disponíveis

- [x] 4.1 Adicionar `{{link_compras}}` apenas ao template WhatsApp de entrega e gerar URL HTTPS a partir do hostname canônico do tenant e do pedido; testar renderização, limite de 500 caracteres, template sem variável, valores maliciosos, isolamento por canal e preservação de `{{pedido}}`/templates anteriores. Evidência: testes focados em `test_notification_settings.py` e `test_tenant_hosts.py`.
- [x] 4.2 Atualizar worker e reenvio para revalidar tenant, cliente, pagamento, álbum e revisão antes do envio; testar provedor falso e mudança do hostname depois do enfileiramento, sem enviar mensagens reais. Evidência: `test_worker_cancels_delivery_if_canonical_host_changes_after_queue` e testes existentes do worker na suíte focada.
- [x] 4.3 Atualizar configuração e prévias do evento para mostrar a variável WhatsApp exclusiva; verificar edição/versionamento, compatibilidade dos seis eventos anteriores e que push continua usando `target_path` sem expor dados de outro tenant. Evidência: testes backend de settings e frontend de notificações.
- [x] 4.4 Reutilizar o `delivery_album_url` por pedido e o evento atual, ampliando a validação de Google Photos para links HTTPS públicos de serviços externos de arquivos; atualizar rótulo/ajuda do campo e testar Google Photos, Drive e outro serviço externo, rejeição de HTTP/credenciais/porta não padrão/host local, preservação de query e que somente o botão da compra do cliente recebe o link externo. Evidência: 25 testes backend e 26 testes frontend direcionados passaram; Google Drive foi usado na regressão de entrega e o teste confirma que somente a projeção da compra contém o link externo.
- [x] 4.5 Usar a origem pública HTTPS confiável somente como hostname compatível quando houver exatamente um tenant ativo sem host persistido; em cenário multitenant, exigir host explícito e falhar fechado para link, OTP e sessão. Cobrir origem diferente recebida pelo cliente, hostname registrado, tenant único, hostname inativo e mais de um tenant ativo. Evidência: `test_tenant_hosts.py` passou com 16 testes, incluindo `test_host_de_tenant_inativo_nao_cai_no_fallback_de_outro_tenant`.
- [x] 4.6 Preservar o evento existente `order_delivery_ready` atrás do interruptor WhatsApp por evento, sem submetê-lo ao gate global reservado aos três novos eventos; cobrir criação, Reenviar aviso e worker com gate global desligado, mantendo os eventos novos bloqueados. Evidência: `pytest tests/test_order_delivery.py tests/test_notification_delivery.py -q --tb=short` (**31 passed**); Ruff focado passou; testes usam provedor sandbox e não enviam mensagens reais.

## 5. Integração e liberação

- [x] 5.1a Executar os testes locais de backend/frontend, validação OpenSpec estrita, lint e typecheck; revisar diff e registrar comandos/resultados em `validation.md`.
- [x] 5.1b Executar migration PostgreSQL descartável e registrar evidência em `validation.md`.
- [x] 5.1c Executar build de produção com dependências instaladas pelo lockfile e registrar o resultado em `validation.md`.
- [x] 5.2a Fazer inventário estático da configuração versionada para orientar a implantação futura e confirmar que esta change não alterou arquivos de DNS/proxy/segredos; registrar limites em `validation.md`.
- [x] 5.2b Inventariar a homologação em modo somente leitura e apresentar plano de impacto zero antes do deploy já autorizado para o hostname existente; manter serviços exclusivos e preservar workers/orphans, sem alterar DNS/TLS/proxy/porta ou enviar mensagem real. Evidência: run `38644817829`, estado e plano em `validation.md`.
- [x] 5.2c Trocar apenas a origem das duas imagens PostgreSQL dos serviços temporários do CI para o mirror com digest idêntico, executar o CI no SHA atual e registrar resultado. Evidência: run `38728087811` aprovou os gates no merge SHA `78954e310a0ae46efe5fec6d7adaeb5ca13cfb8e`; o workflow também executou `deploy-homolog` no host remoto. Não alterar imagens do deploy.
- [ ] 5.3 Revisar o inventário/classificação do host que o workflow chama `deploy-homolog` e decidir um procedimento seguro e explicitamente autorizado para atualizar API/worker de produção; não usar o job automático enquanto o alvo real for tratado como homologação. Evidência e desvio operacional registrados em `validation.md`.

## Workflow follow-up

- Sincronizar specs principais e arquivar somente após implementação validada e revisão humana do resultado.
- Habilitar fotógrafos adicionais somente quando as verificações de isolamento estiverem concluídas e houver aprovação operacional para hostnames e ambiente.
