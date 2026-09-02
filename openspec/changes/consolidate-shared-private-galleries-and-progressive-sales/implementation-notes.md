# Notas de implementação

## Baseline de 2026-09-01 — task 1.1

### Estado preservado

- Branch: `feature/remediate-gallery-workflow-and-payment-experience` acompanhando a origem homônima.
- Worktree antes do código: somente a nova change `consolidate-shared-private-galleries-and-progressive-sales` estava não rastreada; nenhum diff de implementação preexistente foi encontrado.
- Alembic: head único `20260831_0033`.
- Autorização humana: o proprietário autorizou nesta data a higienização necessária de código e banco dentro desta change. A autorização não permite apagar histórico comercial nem dispensa inventário e plano zero-impact antes de homologação/deploy.

### Comandos reproduzíveis

```powershell
rg -l "DerivedGallery\.client_id|gallery\.client_id|derived_gallery.*client_id|client_id.*derived_gallery" backend frontend -g "*.py" -g "*.ts" -g "*.tsx"
rg -l "private_invite|parent_invite|invite_token|GalleryAccessCapability" backend frontend -g "*.py" -g "*.ts" -g "*.tsx"
rg -l "PriceRule|price_rule|price_tier|volume|qr_code_payload|pix_copy_paste|quote\(" backend frontend -g "*.py" -g "*.ts" -g "*.tsx"
rg -l "clone_derived|derived_gallery\.cloned|ensure_private_gallery|derive_client_selection|derive_admin_gallery" backend frontend -g "*.py" -g "*.ts" -g "*.tsx"
Push-Location backend; .\.venv\Scripts\python.exe -m alembic heads; Pop-Location
```

### Inventário de acoplamentos

| Área | Arquivos centrais | Estado encontrado |
| --- | --- | --- |
| Modelo proprietário | `backend/app/auth.py`, migrations `0002`, `0004`, `0012`, `0020`, `0023` | `DerivedGallery.client_id` é obrigatório e único por origem/cliente; não existe associação multiusuário. |
| Resolução e autorização | `backend/app/private_derivation.py`, `backend/app/main.py` | criação, seleção, biblioteca, prévias e mutações resolvem a privada por `DerivedGallery.client_id`. |
| Lifecycle | `backend/app/gallery_cleanup.py`, `backend/app/gallery_lifecycle.py`, `backend/app/private_gallery_lifecycle.py` | inventários e exclusões percorrem privadas e capacidades, mas ainda pressupõem uma proprietária. |
| Capacidades | `backend/app/gallery_access.py`, `backend/app/public_gallery_access.py`, `backend/app/main.py`, migration `0023` | link público é reutilizável; `private_invite` exige `client_id` e o token aleatório não pode ser reconstruído após a resposta inicial. |
| Preço e PIX | `backend/app/pricing.py`, `backend/app/checkout.py`, `backend/app/main.py`, migration `0011` | `quote` escolhe a faixa alcançada e aplica um único valor a todas as unidades; PIX persiste `copy_paste` e `qr_code_payload` separados. |
| Estado individual | `backend/app/auth.py`, `backend/app/checkout.py`, `backend/app/commercial_history.py` | seleções, favoritos, visualizações, comentários e pedidos já têm `client_id`, base adequada para isolamento entre membros. |
| Frontend administrativo | `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx` e testes do editor/preço/pedidos | etapa Vendas ainda edita faixas por galeria; etapa Clientes consome convite individual e não gerencia membros compartilhados. |
| Cobertura existente | `backend/tests/test_derived_galleries.py`, `test_gallery_lifecycle.py`, `test_cloned_gallery_migration.py`, `test_pricing.py`, `test_media.py` | existem regressões para propriedade exclusiva, clone, snapshots, lifecycle, preço legado e prévias; precisam de caracterização explícita antes da transição. |

### Decisões operacionais para a implementação

- Migrations serão aditivas; a proprietária legada permanecerá durante a janela de compatibilidade.
- Conflitos de dados serão diagnosticados e interromperão o upgrade antes de qualquer tentativa de mesclagem.
- Pedidos, itens, snapshots e manifestos históricos não serão removidos nem recalculados.
- A busca facial permanecerá sem endpoint e sem processamento.

## Evidências de execução

### Task 1.2 — caracterização anterior à mudança estrutural

- Adicionados três testes em `backend/tests/test_gallery_lifecycle.py` para snapshots após desligamento operacional, token legado persistido apenas como hash e isolamento por proprietária/cliente.
- Comando: `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_lifecycle.py -k transition_characterization -q`
- Resultado: `3 passed, 44 deselected`.

### Tasks 1.3 e 2.1 — fixtures e modelo de associação

- Criado factory de teste capaz de montar privada legada ou compartilhada.
- Adicionado `DerivedGalleryMembership` com estado controlado, unicidade `parent_gallery_id + client_id`, chave composta que impede associar a origem errada e índices de autorização.
- `DerivedGallery.client_id` foi preservado como proprietária legada durante a compatibilidade.
- Comando: `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_lifecycle.py -k "membership_model or private_gallery_factory or transition_characterization" -q`
- Resultado: `5 passed, 44 deselected`.

### Tasks 2.2 e 2.3 — migration e diagnóstico

- Criada revision aditiva `20260901_0034` com constraint composta da privada, tabela de associações, índices e backfill de cada proprietária legada.
- O diagnóstico ocorre antes de qualquer alteração de schema e aborta em duplicidade origem/cliente sem mesclar registros.
- Comando: `.\.venv\Scripts\python.exe -m pytest tests/test_cloned_gallery_migration.py -k shared_private_membership -q`
- Resultado: `2 passed, 4 deselected`.

### Task 2.4 — serviço transacional de associação

- Criado `app/private_membership.py` com resolução idempotente, ingresso em privada compartilhada, conflito de origem, bloqueio, desbloqueio, desvinculação e reativação/movimentação administrativa explícita.
- A constraint do banco é tratada como árbitro da corrida e o serviço recarrega o vínculo vencedor.
- Comando: `.\.venv\Scripts\python.exe -m pytest tests/test_private_membership.py -q`
- Resultado: `3 passed`.

### Task 2.5 — autorização operacional por associação

- A autorização central e a biblioteca/destino agora priorizam associações ativas; membro bloqueado ou desvinculado é recusado.
- O fallback da proprietária legada existe somente quando a privada não possui associação alguma, impedindo contorno de bloqueio após o backfill.
- Comandos: `.\.venv\Scripts\python.exe -m pytest tests/test_private_membership.py -q` e `.\.venv\Scripts\python.exe -m pytest tests/test_derived_galleries.py -k "library or client_gallery or pending_order_is_private" -q`.
- Resultados: `4 passed` e `2 passed, 48 deselected`.

### Tasks 3.1 e 3.2 — capacidades assinadas e compatibilidade

- Capacidades reconstruíveis usam identificador público, versão e HMAC-SHA256 com segredo dedicado; somente o hash do token final permanece no banco.
- Em ambientes diferentes de desenvolvimento o startup rejeita chave ausente, curta ou reutilizada do segredo de OTP.
- A migration `20260901_0035` adiciona os modos `legacy_random|signed_v1`, versão e o escopo reutilizável `private_gallery_link`, mantendo `private_invite` legado resolvível até seu encerramento.
- Comandos: `.\.venv\Scripts\python.exe -m pytest tests/test_cloned_gallery_migration.py -k shared_private_membership -q` e `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_access_signed.py -q`.
- Resultados: `2 passed, 4 deselected` e `4 passed`.

### Tasks 3.3 a 3.6 — links, OTP e membros

- Endpoints administrativos expõem link público/privado assinado vigente, detectam legado irrecuperável, rotacionam, revogam e mantêm membros.
- OTP privado compartilhado cadastra/reutiliza identidade E.164, associa origem e privada, conserva o link reutilizável, converge para o vínculo já existente e recusa membro bloqueado.
- Endpoints de membros listam, adicionam, bloqueiam, desbloqueiam, desvinculam e reativam sem apagar identidade ou outra privada; conflito na mesma origem retorna `409`.
- Comando principal: `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_access_signed.py -q`.
- Resultado do conjunto de links/OTP: `7 passed`; validação focada de membros após correção: `1 passed, 7 deselected`.

### Tasks 3.7 e 3.8 — notificações e privacidade

- A migration `20260901_0036` cria outbox/painel idempotente; eventos de criação, ingresso, bloqueio, desbloqueio e desvinculação são gravados na transação de domínio.
- O worker processa o canal externo opcional com retentativa; erros persistem apenas a categoria, e falha externa não desfaz o vínculo.
- Contratos de biblioteca, revisão, comentários e pagamentos foram exercitados com duas clientes da mesma privada e não serializaram identidade, comentário, seleção ou valor da outra.
- Comandos focados: `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_access_signed.py -k "admin_manages_private_members or membership_notification_outbox" -q` e `... -k client_contracts_do_not_serialize -q`.
- Resultados: `2 passed, 7 deselected` e `1 passed, 9 deselected`.

### Tasks 4.1 a 4.3 — modelo e cálculo de preço progressivo

- A revision `20260901_0037` cria presets globais versionados, suas faixas e o snapshot comercial da Galeria pública; uma faixa legada é convertida em preço fixo e configurações com várias faixas ficam como `legacy_volume`, exigindo revisão explícita sem recalcular pedidos.
- A cotação progressiva cobra cada intervalo pelo preço correspondente, detalha parcelas e calcula economia contra o preço da primeira faixa. Preços crescentes e intervalos descontínuos são recusados.
- Comandos: `.\.venv\Scripts\python.exe -m pytest tests/test_cloned_gallery_migration.py -k progressive_pricing_migration -q --tb=short` e `.\.venv\Scripts\python.exe -m pytest tests/test_pricing.py tests/test_cloned_gallery_migration.py -k "pricing or progressive" -q --tb=short`.
- Resultados: `1 passed, 6 deselected` e `11 passed, 6 deselected`.

### Tasks 4.4 a 4.6 — presets, snapshots por galeria e PIX único

- O backend lista, cria, edita com incremento de versão, desativa e simula tabelas globais. A Galeria pública aceita preço fixo ou preset ativo e materializa código, nome, versão e faixas; alterar o preset não muda o snapshot já salvo.
- Configurações `legacy_volume` exigem confirmação explícita antes da conversão. O contrato anterior de uma faixa permanece compatível como preço fixo durante a transição.
- PIX copia-e-cola passou a ser a única fonte operacional, com validação BR Code/CRC e QR PNG gerado localmente. A migration `20260901_0038` converge valores equivalentes/isolados e marca divergências antigas para revisão.
- Comandos: `.\.venv\Scripts\python.exe -m pytest tests/test_derived_galleries.py -k "progressive_pricing_presets or materializes_pricing" -q --tb=short` e `.\.venv\Scripts\python.exe -m pytest tests/test_pix.py tests/test_derived_galleries.py tests/test_cloned_gallery_migration.py -k "pix_source or gallery_pix or test_pix" -q --tb=short`.
- Resultados: `2 passed, 50 deselected` e `4 passed, 59 deselected`.

### Task 4.7 — cotação única e pedido imutável

- Carrinho e checkout usam `quote_parent_gallery`; configurações legadas pendentes são bloqueadas e o pedido congela modo, preset, faixas, parcelas, economia, total, prazo, PIX e condição de confirmação manual.
- Itens progressivos recebem os valores unitários das parcelas de forma determinística, e repetir a mesma chave de checkout devolve o pedido original sem recalcular.
- Comando: `.\.venv\Scripts\python.exe -m pytest tests/test_derived_galleries.py -k "cart_and_checkout_share_progressive" -q --tb=short`.
- Resultado: `1 passed, 53 deselected`.

### Tasks 5.1 a 5.3 — acervo compartilhado e estado individual

- Derivação administrativa e manual agora resolvem a associação única da origem; membros de uma mesma privada adicionam referências ao mesmo acervo sem criar nova galeria nem duplicar `PhotoAsset`.
- A revision `20260901_0039` consolida uma única referência por `galeria + foto`, preservando a mídia original. Seleção, favorito, comentário, visualização, compra e pagamento permanecem sempre associados ao `client_id` autenticado.
- Comandos: `.\.venv\Scripts\python.exe -m pytest tests/test_private_membership.py -q --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_cloned_gallery_migration.py -k "progressive_pricing_migration or pix_source" -q --tb=short` e `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_access_signed.py -k client_contracts_do_not_serialize -q --tb=short`.
- Resultados: `5 passed`, `2 passed, 6 deselected` e `1 passed, 9 deselected`.

### Tasks 5.4 e 5.5 — DTO administrativo e biblioteca

- A listagem administrativa de membros ganhou paginação, filtro de estado e agregados de seleção, compras, pedidos, total confirmado e pagamento por cliente mediante subconsultas agrupadas; o teste limita a quantidade de `SELECT`s para prevenir N+1.
- A biblioteca agrupa uma privada por origem, mostra bloqueio sem permitir navegação, mantém navegação das associações ativas e conserva o histórico confirmado mesmo após bloqueio ou remoção operacional.
- Comando: `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_access_signed.py -k "admin_manages_private_members or library_routes" -q --tb=short`.
- Resultado: `2 passed, 9 deselected`.

### Tasks 5.6 e 5.7 — lifecycle e gate facial

- A exclusão pública revoga todas as capacidades da origem, preservando privadas, associações e fotos nelas referenciadas. A desvinculação remove somente registro, estados da cliente e capacidades individuais, marca a associação como `unlinked` e mantém acervo, demais membros e histórico.
- Inventário e execução foram reconciliados com a nova granularidade; a porta facial continua interna, sempre indisponível e sem rota HTTP.
- Comandos: `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_lifecycle.py::test_parent_gallery_deletion_endpoint_is_idempotent_and_returns_inventory tests/test_gallery_lifecycle.py::test_record_cleanup_removes_public_origin_and_preserves_private_graph tests/test_gallery_lifecycle.py::test_public_deletion_keeps_one_private_photo_copy_and_private_viewing tests/test_gallery_lifecycle.py::test_unlink_client_is_idempotent_scoped_and_preserves_history -q --tb=short` e `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_lifecycle.py -k facial -q --tb=short`.
- Resultados: `4 passed` e `1 passed, 48 deselected`.

### Task 6.1 — documentação local do Next.js

- Versão instalada confirmada: Next.js `16.3.2`.
- Arquivos locais lidos antes de editar o frontend: `frontend/AGENTS.md`, `frontend/node_modules/next/AGENTS.md`, `dist/docs/01-app/index.md`, `dist/docs/01-app/01-getting-started/04-linking-and-navigating.md`, `07-mutating-data.md` e `13-fonts.md`.
- Decisões aplicadas: preservar App Router; usar navegação cliente com feedback pendente onde apropriado; tratar mutations como operações autenticadas e com estado de erro; manter fontes empacotadas/localmente servidas, sem requisição remota no navegador.

### Task 6.2 — tabelas globais progressivas

- Criada a entrada administrativa `Tabelas de preço` e a tela responsiva de cadastro, listagem, edição versionada e desativação de presets, com intervalos contíguos e valores digitados/mostrados em BRL.
- A interface comunica que a desativação não altera snapshots já aplicados a galerias e inclui estados de carregamento, vazio e erro.
- Comando: `npx vitest run app/admin/pricing/page.test.tsx --reporter=verbose`.
- Resultado: `3 passed`, cobrindo moeda brasileira, versões/faixas e criação com payload em centavos.

### Task 6.3 — etapa Vendas

- A etapa 02 agora alterna entre preço fixo em BRL e preset global pelo rótulo `código — nome`, sem permitir edição local das faixas; a simulação progressiva consulta o endpoint autoritativo e mostra parcelas, total e economia.
- O frontend envia somente PIX copia-e-cola e instruções, mostra o QR PNG gerado pelo backend e sinaliza divergência antiga. `legacy_volume` exige escolha e confirmação explícitas antes da conversão.
- Comando: `npx vitest run app/admin/galleries/gallery-editor.test.tsx --reporter=verbose`.
- Resultado: `29 passed`, incluindo recarga de preço fixo, erro preservando dados, conversão legada, simulação progressiva e QR sem campo de payload.

### Task 6.4 — salvar, avançar e estado sujo

- As etapas editáveis 01–03 usam uma única ação `Salvar e avançar`, navegam somente após resposta bem-sucedida e desabilitam a submissão durante a mutation.
- Troca pelo stepper, retorno à listagem, retorno para a etapa anterior e fechamento da página são protegidos quando há alteração não salva; falha do backend preserva o formulário e não navega.
- Comando: `npx vitest run app/admin/galleries/gallery-editor.test.tsx --reporter=verbose`.
- Resultado: `31 passed`, incluindo sucesso, falha, clique repetido e descarte negado/confirmado.

### Task 6.5 — links e membros na etapa Clientes

- A etapa 05 carrega, exibe, copia, cria e regenera os links assinados da Galeria pública e de cada privada; a rotação informa a revogação do endereço anterior.
- Cada privada ganhou painel de membros com agregados individuais, inclusão, bloqueio, desbloqueio e desvinculação. O fluxo administrativo de criação por fotos continua sem seleção automática.
- O DTO compatível de clientes da Galeria pública foi corrigido para resolver a privada por associação, calcular disponíveis/selecionadas pela cliente e expor `membership_status`, inclusive para o segundo membro do mesmo acervo.
- Comandos: `npx vitest run app/admin/galleries/gallery-editor.test.tsx -t "links estáveis|conflito|carregamento e erro|galeria privada criada" --reporter=verbose` e `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_access_signed.py -k "admin_manages_private_members" -q --tb=short`.
- Resultados: `3 passed` no recorte frontend e `1 passed, 10 deselected` no backend; os cenários cobrem vazio, carregamento, erro, conflito, cópia/rotação e associação multiusuário.

### Task 6.6 — resumo público e detalhe privado

- O resumo público mantém capa e miniaturas de pastas navegáveis para a etapa de upload. O detalhe privado foi refeito por pastas, prévias protegidas, inclusão de fotos publicadas e remoção apenas da justificativa administrativa, sem apagar o JPEG da origem.
- A inconsistência de múltiplas justificativas foi corrigida pela migration aditiva `20260901_0040`: a referência de acervo continua única, mas origens `admin|client|facial` são independentes. Uma seleção existente mantém a foto quando o fotógrafo remove sua inclusão.
- Cards da privada usam os agregados por membro e abrem seleção/exportação com `client_id`; o backend passou a filtrar também itens confirmados e exportação pela cliente escolhida.
- Comandos: `npx vitest run app/admin/galleries/galleries.test.tsx --reporter=verbose`, `.\.venv\Scripts\python.exe -m pytest tests/test_private_membership.py -q --tb=short`, `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_access_signed.py -k "admin_manages_private_members or private_acervo" -q --tb=short` e `.\.venv\Scripts\python.exe -m pytest tests/test_cloned_gallery_migration.py -k "private_photo_origins" -q --tb=short`.
- Resultados: `5 passed` frontend, `5 passed` no serviço, `2 passed, 10 deselected` nos contratos administrativos e `1 passed, 8 deselected` na migration.

### Task 6.7 — tipografias locais

- O registro controlado passou a oito opções: três sem serifa/arredondadas, duas editoriais e três manuscritas. Fontes empacotadas continuam servidas por `@fontsource`; as opções de sistema têm pilhas locais e fallback acessível, sem URL remota.
- Backend e frontend compartilham os mesmos tokens, IDs arbitrários continuam rejeitados/fazem fallback seguro e a prévia reativa usa a variável CSS selecionada.
- Comandos: `.\.venv\Scripts\python.exe -m pytest tests/test_gallery_workflow_remediation.py -k "cover_font" -q --tb=short`, `npx vitest run app/gallery-fonts.test.ts app/admin/galleries/gallery-editor.test.tsx -t "registro local|tipografia|capa pronta" --reporter=verbose` e `npm run build`.
- Resultados: `1 passed, 7 deselected`, `3 passed, 33 skipped` e build de produção Next.js `16.3.2` concluído com 17 páginas estáticas/dinâmicas e sem download de fonte remota.

### Task 6.8 — central de notificações administrativas

- A navegação administrativa ganhou uma central própria para eventos de criação de privada e entrada, bloqueio, desbloqueio ou desvinculação de membros, separada das telas comerciais e de mensagens.
- A tela oferece filtros por leitura e tipo de evento, marcação de leitura, cards responsivos e deduplicação defensiva por identificador. O contrato visual usa somente snapshots de nomes e identificadores de navegação; telefone, seleções, pedidos, pagamentos e valores não são exibidos.
- Comando: `npm test -- --run app/admin/notifications/page.test.tsx app/admin/admin-navigation.test.tsx` seguido de `npx tsc --noEmit`.
- Resultado: `3 passed` e typecheck concluído sem erros, cobrindo deduplicação visual, filtros, leitura e ausência de telefone/valor comercial.

### Tasks 7.1 e 7.2 — entrada contextual e acervo privado compartilhado

- A entrada preserva a capacidade opaca e o retorno durante o OTP, normaliza celular brasileiro em E.164 com `+55` e nono dígito e usa o destino autorizado pelo backend. Sessão existente somente retoma vínculo já permitido; novas origens e privadas continuam exigindo o desafio contextual.
- Biblioteca e privada renderizam o acervo comum, mas favoritos, seleção e estado de compra vêm exclusivamente do contrato da cliente atual. A grade adaptativa usa prévias autenticadas, proteção contra cópia direta, navegação por pasta e marcadores acessíveis sem listar membros.
- Comandos: `npm test -- --run app/auth-entry.test.tsx app/public-galleries/public-gallery.test.tsx app/library/library.test.tsx`, `npm test -- --run app/gallery/gallery.test.tsx app/gallery-presentation.test.tsx app/library/library.test.tsx`, `pytest tests/test_gallery_access_signed.py -k "private_link or conflict or blocked or existing_session"` e `... -k client_contracts_do_not_serialize`.
- Resultados: `20 passed`, `17 passed`, `5 passed, 7 deselected` e `1 passed, 11 deselected`.

### Tasks 7.3 e 7.4 — rodapé comercial e conferência PIX

- Após a primeira seleção, o rodapé responsivo mostra a quantidade autoritativa, total, economia e decomposição progressiva recebida de `/cart`; remover ou adicionar foto recarrega a mesma cotação do backend. `Prosseguir` cria o pedido com chave estável durante retentativas.
- A conferência busca o snapshot imutável do pedido, lista miniaturas e nomes, exibe QR gerado no servidor, PIX copia-e-cola, instruções, total/economia e a ação `Informar pagamento`. A comunicação usa chave estável, impede clique concorrente e muda para `O pagamento está em análise` sem confirmação automática.
- Comandos: `npm test -- --run app/gallery/gallery.test.tsx`, `npx tsc --noEmit` e `pytest tests/test_derived_galleries.py -k "cart_and_checkout_share_progressive or client_reports_own_pending_payment_idempotently"`.
- Resultados: `9 passed`, typecheck sem erros e `2 passed, 52 deselected`.

### Tasks 7.5 e 7.6 — privacidade comercial e gate facial

- Pedido, PIX, comunicação, confirmação personalizada e histórico permanecem vinculados à cliente do pedido. A confirmação enfileira somente o telefone congelado dessa cliente; outro membro da mesma privada não recebe valores, decisão ou itens.
- A busca facial segue sem rota ou interface de upload, consentimento ou promessa de resultado. O único token `facial` do frontend é o tipo administrativo da justificativa interna futura, sem controle visível ou envio biométrico.
- Comandos: `pytest tests/test_derived_galleries.py tests/test_gallery_access_signed.py -k "client_contracts_do_not_serialize_other_member_or_commercial_activity or admin_confirms_payment_communication_once or client_reads_only_own_pending_order"`, busca `rg` no frontend e `npm run build`.
- Resultados: `2 passed, 64 deselected`; build Next.js `16.3.2` concluído com 18 páginas, incluindo a nova central de notificações, sem interface facial.

### Task 8.1 — qualidade backend e schema

- A suíte completa foi executada após reconciliar associações multiusuário, origens de fotos, lifecycle, links compartilháveis, resumo legado e configuração de assinatura. O lint final também cobre todo `app` e `tests`.
- A configuração final usa `GALLERY_CAPABILITY_SIGNING_KEY` como segredo dedicado e a rejeita quando ausente, curta ou igual a `AUTH_PII_FINGERPRINT_SALT`. O Compose recebe apenas a referência externa; nenhum valor real foi lido ou gravado.
- Comandos: `python -m ruff check app tests`, `python -m pytest -q --tb=short`, teste focado de configuração/WhatsApp e `alembic heads`.
- Resultados: Ruff sem ocorrências; `235 passed, 1 skipped` em `1279.99s`; teste focado `1 passed, 37 deselected`; head único `20260901_0040 (head)`.

### Task 8.2 — qualidade frontend

- A validação integral cobriu a central administrativa, configuração comercial, editor, biblioteca, autenticação contextual, apresentação e checkout do cliente.
- Comandos: `npm run lint`, `npx tsc --noEmit`, `npm test -- --run` e `npm run build`.
- Resultados: lint sem erros e com 22 avisos conhecidos de imagens protegidas/navegação; TypeScript sem erros; `24` arquivos e `117` testes aprovados; build Next.js `16.3.2` concluído com `18` rotas.

### Task 8.3 — matriz sintética de integração

- O ciclo foi exercitado sem dado real: capacidade privada, OTP e identidade reutilizada; vínculo único por origem; privada com múltiplos membros; isolamento contratual; biblioteca; cotação progressiva e snapshot; pedido; comunicação de pagamento idempotente; confirmação administrativa; remoção operacional e preservação de histórico/referência administrativa.
- Comando: `pytest` com oito cenários nomeados em `test_gallery_access_signed.py`, `test_derived_galleries.py` e `test_gallery_lifecycle.py`.
- Resultado: `8 passed` em `46.67s`.

### Tasks 8.4 e 8.5 — revisão integral e gate de homologação

- `git diff --check` ficou limpo, salvo avisos informativos de conversão LF/CRLF; a busca por padrões de segredo não encontrou credencial. A produção não contém fonte remota nem rota/interface facial; a única URL WOFF2 externa é um valor malicioso proposital em teste negativo.
- `docker compose --env-file .env.example -p markina-gallery -f docker/docker-compose.yml config --quiet` passou sem alterar ou iniciar recursos. A validação `npx --yes @fission-ai/openspec validate consolidate-shared-private-galleries-and-progressive-sales --strict` declarou a change válida.
- O inventário `deployment-inventory.md` registra migrations `0034–0040`, topologia preservada, novo segredo dedicado, backup, smoke sintético, rollback conservador e os gates humanos. Nenhuma ação remota foi executada.

### Task 8.6 — preparação operacional autorizada

- Antes do push autorizado, a automação foi reconciliada com o novo requisito de startup: `deploy-homolog.sh` agora gera `GALLERY_CAPABILITY_SIGNING_KEY` no próprio servidor quando ausente, preserva o arquivo seguro em `0600`, recusa duplicidade, valor curto ou reutilização de `AUTH_PII_FINGERPRINT_SALT` e não imprime o material secreto.
- Comandos: Git Bash `scripts/test_deploy_homolog.sh`, `python scripts/test_deploy_homolog_policy.py` e `git diff --check`.
- Resultados pré-deploy: teste shell e política estrutural aprovados; somente avisos informativos LF/CRLF. Hardening versionado em `9d7a54c6f98a0ac6972441e95513e41ae4d52398`.

### Task 8.6 — deploy e paridade de homologação

- O PR `#27` integrou o artefato em `develop` como `f2ba6dc23d5d896daa95c654a2f2539a9cd89664`. O run `33624664090` concluiu backend, frontend, OpenSpec, gitleaks e `deploy-homolog` com sucesso; o deployment do Environment `homolog` é `6221341108`.
- O script gerou `GALLERY_CAPABILITY_SIGNING_KEY` somente no servidor sem imprimir o valor, registrou inventário restrito à Markina, criou backup lógico e avançou Alembic de `20260831_0033 (head)` para `20260901_0040 (head)`. Apenas `api`, `web`, `worker` e `nginx` foram recriados; não houve `down`, prune ou alteração de recursos de terceiros.
- Às `2026-09-02T11:32:25Z` e `11:32:26Z`, `https://markina-homolog.duckdns.org/healthz` respondeu `200`/`ok` e `/api/health` respondeu `200`/`{"status":"ok","service":"api"}`. A entrada retornou `200`; as APIs administrativas novas recusaram sessão ausente com `403`, sem vazar dados.
- Smoke sintético do mesmo SHA: backend `235 passed, 1 skipped`, frontend `117 passed`, build com 18 rotas, OpenSpec e gitleaks verdes; a matriz dirigida de link, OTP, vínculo, isolamento, cotação, pedido, pagamento e lifecycle havia aprovado `8/8`. A sessão de navegador disponível não possuía autenticação administrativa válida, portanto nenhuma credencial foi inferida nem dado persistente criado; o ciclo visual autenticado permanece corretamente na revisão humana 8.7.

### Tasks 8.7.1 a 8.7.6 — correções da primeira revisão humana

- Campos monetários da etapa Vendas e das tabelas globais agora aplicam máscara financeira brasileira durante a digitação e continuam persistindo centavos inteiros. A entrada numérica `700` resulta em `R$ 7,00`; milhares recebem ponto e centavos recebem vírgula.
- O endpoint de desvinculação já estava funcional e protegido contra pagamento informado ainda em análise. A falha percebida vinha do feedback global ficar oculto atrás do modal; confirmação, erro, progresso, conclusão, cancelamento e retentativa agora permanecem junto ao cartão acionado.
- `Disponibilizar fotos` não fica mais silenciosamente desabilitado. Sem fotos elegíveis, o modal explica que somente fotos processadas e publicadas podem entrar na privada e leva diretamente à etapa Imagens; erros de criação/atualização permanecem dentro do modal.
- Exclusões pública e privada agora usam confirmação contextual e mantêm erro/bloqueio junto à ação. A pública preserva o acompanhamento assíncrono; a privada explicita a preservação de clientes e histórico comercial.
- O contrato vigente de PIX aceita o BR Code/EMV completo, com CRC válido, como única fonte do QR. A interface agora distingue esse código de uma chave simples e recusa localmente e-mail, CPF, telefone ou chave aleatória no campo de copia-e-cola. Suportar geração a partir de chave simples exigiria, em change própria, dados adicionais do recebedor (ao menos nome e cidade) e definição de armazenamento; nenhum QR incompleto foi improvisado.
- Os modos `standard`, `invite_only` e `collective_protected` continuam ativos no backend e não são obsoletos. A etapa 01 agora explica respectivamente link + OTP com navegação pública, convite individual e solicitação protegida sem grade coletiva/reconhecimento facial.
- Validação dirigida: `npm test -- --run app/admin/galleries/gallery-editor.test.tsx app/admin/galleries/galleries.test.tsx app/admin/pricing/page.test.tsx` resultou em `48 passed`; `pytest tests/test_pix.py tests/test_gallery_lifecycle.py -q --tb=short` resultou em `51 passed`.
- Validação integral frontend: `npm test -- --run` resultou em `24` arquivos e `123 passed`; `npx tsc --noEmit` e `npm run build` concluíram sem erros, com 18 páginas geradas. A task 8.7 principal permanece aberta até nova aprovação humana em homologação.

### Tasks 8.7.7 e 8.7.8 — diretório, edição e exclusão protegida de clientes

- A etapa 05 deixou de filtrar cadastros já vinculados: todas as correspondências continuam em `Cadastro existente`, com estado `Já vinculada`, ação redundante de vínculo ausente e edição disponível.
- Nome é atualizado sobre o mesmo `Client.id`. A troca de telefone reutiliza o desafio OTP enviado ao novo WhatsApp, a unicidade E.164 e a aposentadoria do número anterior, preservando galerias e snapshots comerciais.
- A exclusão direta possui inventário autoritativo e só aceita cadastros sem acesso, vínculo, sessão, OTP, comunicação, interação ou pedido. Troca de telefone não exige exclusão; conflito concorrente durante a remoção retorna `409` e não produz deleção parcial.
- Comandos dirigidos: `pytest tests/test_derived_galleries.py -k 'client_deletion or edits_and_deletes_client or cannot_delete_client' -q` e `npm test -- --run app/admin/galleries/gallery-editor.test.tsx`.
- Resultados: backend `3 passed, 54 deselected`; frontend `41 passed`, incluindo permanência do cadastro vinculado, edição de nome, OTP do novo telefone e bloqueio visual por pedido.
- Validação integral: backend `241 passed, 1 skipped`; frontend `24` arquivos e `126 passed`; Ruff sem ocorrências; ESLint sem erros (22 avisos preexistentes), TypeScript sem erros e build Next.js `16.3.2` concluído com 18 rotas.

### Task 8.7.9 — preparação da limpeza autorizada de homologação

- Foi criada uma operação fora da API pública, guardada por `APP_ENV=homolog|homologation`, diretório `/opt/markina-gallery`, projeto Compose fixo, confirmação literal e Environment `homolog`. O inventário não serializa PII; a execução cria backup lógico, pausa somente API/worker da Markina, limpa banco/Redis/mídia exclusivos e preserva administrador, configurações e pareamento WhatsApp.
- O acionamento destrutivo é efêmero e exige o trailer exato `Homolog-Cleanup: galleries-and-clients` no commit aprovado; pushes comuns executam somente inventário. Não há `down`, prune, glob amplo ou recurso de terceiro no fluxo.
- A rotina foi validada em PostgreSQL 17 temporário e isolado com uma cliente e uma galeria sintéticas: contagens `1 → 0` para ambas e administrador preservado. O container temporário foi removido após a prova.
- Comandos: `bash -n scripts/maintain-homolog-data.sh`, `scripts/test_deploy_homolog.sh`, `pytest tests/test_homolog_cleanup.py ...`, prova PostgreSQL e `openspec validate ... --strict`.
- Estado: implementação e inventário real validados; backup, limpeza e verificação remota foram autorizados e permanecem pendentes do acionamento destrutivo auditável em homologação.
- Na primeira publicação do mecanismo, o deploy do SHA `67fff84b8646cbd1b223d67bdbabfb5fe6a5bed9` ficou saudável, mas o inventário abortou antes de ler ou alterar dados porque o container `compose run --no-deps` não herdou `APP_ENV`. A correção injeta `APP_ENV=homolog` somente no container efêmero já protegido por Environment, host, diretório, projeto e arquivo de ambiente fixos; nenhuma exclusão ocorreu nessa tentativa.
- O deploy corretivo `c1b11683842cc01393bf557bac59ec3d1fcd1d44`, run `33658598348` e deployment `6227653125` concluiu verde com Alembic `20260901_0040 (head)`. O inventário real, sem PII, encontrou `3` clientes, `3` galerias públicas, `3` derivadas, `12` fotos, `3` pedidos, `45` arquivos-fonte (`28.584.497` bytes) e `135` derivados (`39.483.437` bytes), além dos vínculos, desafios e comunicações associados. A execução destrutiva separada permanece limitada a esses recursos Markina e foi autorizada pelo proprietário após apresentação do inventário e plano de impacto.
- O run `33659814824` confirmou o gatilho no SHA `741ea5091ddaf43d93637bea5afb5804acc7decf`, mas a manutenção terminou após `compose ps`, antes do backup, sem excluir dados: o subprocesso herdou a entrada padrão usada por `bash -s` para transportar a própria rotina. A correção fecha a entrada padrão para toda chamada Compose e possui teste estrutural para impedir regressão antes de repetir a operação autorizada.
- A execução corrigida ocorreu no SHA `2eab180af1965449e4d97f2462ef78e17d92f5cb`, run `33660598130`, job `100350603087` e deployment `6227981908`, todos verdes. Um novo backup lógico exclusivo da Markina foi criado antes da pausa restrita de API/worker; o inventário pós-operação confirmou zero em clientes, galerias públicas/derivadas, fotos, vínculos, pedidos, comunicações, sessões, desafios OTP, entregas WhatsApp e operações de ciclo de vida, além de zero arquivos/bytes nos três volumes de mídia.
- Alembic permaneceu em `20260901_0040 (head)` e todos os containers Markina/Evolution voltaram saudáveis. Após o término, `https://markina-homolog.duckdns.org/healthz` respondeu `200`/`ok` e `/api/health` respondeu `200`/`{"status":"ok","service":"api"}`. Administrador, configurações, tabelas de preços, pareamento WhatsApp e recursos Evolution não fizeram parte das raízes excluídas; a task `8.7.9` está concluída, enquanto a revisão humana `8.7` permanece aberta.

### Tasks 8.7.10 a 8.7.13 — segunda revisão humana

- A configuração PIX aceita BR Code completo ou chave simples por CPF válido, telefone brasileiro ou e-mail. Chaves simples exigem nome e cidade públicos do recebedor, são normalizadas e geram BR Code estático/QR local com CRC; a entrada estruturada permanece editável e o pedido continua congelando somente o código operacional. A migration aditiva e reversível `20260902_0041` acrescenta os quatro campos estruturados e classifica configurações anteriores como `br_code`.
- A falha `preparing_history` da desvinculação foi reproduzida no SQL compilado para PostgreSQL: `SELECT DISTINCT ... FOR UPDATE` é inválido nesse banco mesmo quando não existem pedidos. A consulta passou a bloquear `sale_order` sem `DISTINCT` e usa subconsulta de IDs para o recorte por foto; o ciclo idempotente sem privada/pedido preserva cadastro e histórico.
- `Salvar e avançar` em Imagens chama um endpoint transacional que publica todas as prévias prontas da Galeria pública. Processamento ou falha mantém a etapa aberta com contagens; só a rodada integralmente pronta abre Clientes. A ação separada passou a se chamar `Montar galeria privada` e deixa explícito que não favorita, seleciona nem compra em nome da cliente.
- Vínculo administrativo passou a aparecer como `Aguardando primeiro acesso` enquanto o telefone ativo não tiver `verified_at`. O vínculo pré-autoriza acesso à Galeria pública, mas a primeira abertura do link continua exigindo OTP; `Sem pedido` permanece correto até seleção e checkout.
- Validação focada: `10 passed` no conjunto PIX/API/status/lifecycle/publicação/migration; teste adicional de consulta agregada `1 passed`; migration `0041` com upgrade/downgrade `5 passed` junto ao módulo PIX. O frontend dirigido aprovou `42` testes.
- Validação integral final: backend `248 passed, 1 skipped`; Ruff sem ocorrências; frontend `24` arquivos e `127 passed`; ESLint, TypeScript e build Next.js `16.3.2` sem erros, com `18` páginas. Head Alembic único `20260902_0041`; Compose, políticas de deploy, `git diff --check` e os `26` itens OpenSpec estritos aprovados.
- O PR `#37` integrou o incremento como `f68a5ce205e3619045e3261b377c981778ab42c8`. O run `33688843960` e o deployment `6232831214` concluíram verdes; backup lógico foi criado, Alembic avançou de `0040` para `0041` e somente `api`, `web`, `worker` e `nginx` foram recriados. Às `22:13:15Z` e `22:13:16Z`, `/healthz` e `/api/health` responderam `200`; homologação está em paridade e aguarda o reteste humano da task 8.7.
