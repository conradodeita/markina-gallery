# Continuidade — PIX global

## Escopo ativo em 2026-09-06

A solicitação atual prioriza mover PIX para Configurações. Executar as tarefas PIX (1.3, partes PIX de 2.1–2.4, 5.1–5.5, 6.1–6.4, 7.2 e validação/documentação correspondentes). O diretório/lifecycle de clientes permanece planejado, fora desta solicitação; não marcar suas tarefas nem considerar a change inteira concluída.

## Inventário anterior à implementação

- `auth.PixCheckoutSettings` contém chave/BR Code, recebedor, cidade, instruções e revisão por `parent_gallery_id` único. Migration vigente: `20260906_0045`.
- `main.pricing_payload` e `save_parent_pricing` expõem/escrevem PIX nas rotas `/admin/parent-galleries/{id}/pricing` e `/sales`; privadas consultam o mesmo contrato somente leitura.
- `checkout.create_pending_checkout` lê PIX da origem e grava copia-e-cola/instruções no `SaleOrder`; leitura do pedido usa snapshots. Preservar esses snapshots e acrescentar metadados da versão/recebedor.
- `gallery-editor.tsx` edita e valida PIX no avanço da etapa 02; `admin/settings/page.tsx` já compõe painéis WhatsApp e Segurança.
- `admin_account` disponibiliza senha atual, desafio de 10 minutos, limite de cinco tentativas, payload cifrado, vinculação de sessão e entrega administrativa por WhatsApp. A confirmação PIX deve consumir o desafio atomicamente com a atualização e serializar mudanças concorrentes.
- A nova decisão substitui exclusivamente a escrita PIX por galeria prevista em `consolidate-shared-private-galleries-and-progressive-sales`. Preços continuam por galeria e snapshots antigos permanecem legíveis conforme `add-manual-pix-checkout`.
- O backend recusará qualquer campo `pix` nas escritas por galeria (422 orientativo). Frontend atualizado omite o campo; sessões antigas precisam atualizar a página. Não há override nem fallback silencioso ao legado.
- Migração aditiva conserva `pix_checkout_settings`. Dados divergentes/inválidos não elegem recebedor: revisão obrigatória. Nome/cidade do BR Code serão extraídos do próprio código para preservar equivalência canônica com chave simples.
- O trabalho facial anterior foi preservado e publicado junto do PIX global após inventário e limpeza autorizada de dados de teste; o estado remoto validado está registrado abaixo.

## Implementação e contratos

- `GET /admin/settings/pix`: leitura administrativa da configuração global, QR e versão. Clientes e anônimos recebem 403.
- `POST /admin/settings/pix/challenge`: senha atual e `configuration` (chave/BR Code, recebedor, cidade, instruções) ou `null` para remoção. Retorna 202, UUID do desafio, prazo e prévia normalizada do PIX proposto. Essa prévia usa o recebedor contido no BR Code, nunca campos antigos do formulário. Não salva a configuração.
- `POST /admin/settings/pix/confirm`: somente UUID do desafio e OTP. Sessão, conteúdo cifrado/fingerprint, expiração de 10 minutos, cinco tentativas e versão são conferidos. A configuração e o consumo do desafio são transacionais; emissão e confirmação serializam pelo administrador. Mudança concorrente exige nova confirmação.
- `/admin/settings#pix`: painel para cadastrar, alterar e remover PIX. A etapa Vendas e a configuração da privada explicam a origem global. Salvar/avançar na galeria não envia PIX.
- Escrita legada de PIX por galeria retorna 422 com orientação para atualizar a página. Não existe override nem fallback ao PIX legado para novos pedidos.
- Novo checkout usa somente configuração ativa; congela BR Code/instruções e UUID/versão/recebedor/cidade no pedido. O QR é gerado a partir desse BR Code congelado. Ausência, revisão ou remoção impedem novos pedidos, mas conservam seleções e pedidos idempotentes já existentes.
- Nenhuma variável, segredo ou credencial foi criada/alterada. A confirmação reutiliza o canal administrativo WhatsApp já configurado.

## Uso pelo fotógrafo

1. Abrir Configurações → PIX → Configurar/Alterar PIX.
2. Informar CPF, telefone brasileiro, e-mail ou copia-e-cola. Chave simples exige nome e cidade do recebedor.
3. Informar senha atual, solicitar o código e conferir a prévia da alteração. Confirmar o OTP recebido no WhatsApp administrativo.
4. Novos pedidos de todas as galerias passam a usar essa versão. Preços e tabelas continuam definidos por galeria. Remover PIX exige a mesma confirmação.

## Migração e rollback

`20260906_0046` sucede `20260906_0045`: cria `global_pix_settings`, acrescenta snapshot JSON nullable ao pedido e amplia o propósito dos desafios. Mantém integralmente `pix_checkout_settings` e os campos comerciais existentes.

O backfill compara BR Code e instruções canônicos: sem valor → `unconfigured`; equivalentes (inclusive chave vs. BR Code) → versão 1 ativa; divergência, código inválido ou revisão legada → `review_required`. Sem administrador não cria proprietário artificial; com mais de um, aborta para revisão.

Rollback preferencial é da aplicação com schema aditivo preservado. Antes de liberar novos checkouts na versão antiga, conferir o PIX legado: mudanças globais não foram replicadas para galerias. Downgrade estrutural é recusado quando há desafios PIX ou snapshots globais de pedidos; não apagar esses registros para forçar a reversão.

## Evidências locais — 2026-09-06

- `tests/test_derived_galleries.py`: **58 passed**, após adaptar os fixtures comerciais ao contrato global e preservar os testes de preço, seleção, pagamento e leitura privada.
- `tests/test_global_pix.py tests/test_admin_security.py tests/test_pix.py`: **39 passed**; após reforçar a prévia canônica, `tests/test_global_pix.py`: **16 passed**.
- Migration SQLite: quatro cenários passaram. PostgreSQL 16 descartável: **4 passed**, incluindo equivalência chave/BR Code, rejeição de downgrade com snapshot global, preservação dos campos legados e downgrade seguro sem novos dados. Container exclusivamente sintético `markina-gallery-pix-validation`, publicado só em `127.0.0.1:55446`, encerrado após validar; nenhum banco do produto foi alterado.
- Frontend completo: **147 testes / 27 arquivos**. Após reforçar a prévia, **48 testes** das três suítes afetadas passaram. Typecheck e build concluídos; lint sem erros, com 22 avisos (imagens/navegação, incluindo QR local).
- Ruff passou em app, testes e migration. OpenSpec estrito: **28/28**. Gitleaks dos arquivos alterados/novos: sem achados. `git diff --check`: sem erros.
- A primeira suíte backend completa reportou **337 passed, 10 failed, 1 skipped**: os dez erros eram contratos/fixtures PIX antigos em `test_derived_galleries.py`; a suíte desse arquivo foi corrigida e passou integralmente. A execução completa final passou: **364 passed, 1 skipped** em 27m21s.
- Conferência visual autenticada e sintética em desktop e viewport 390×844 confirmou a presença do PIX em Configurações, QR, estado/versão, formulário e adaptação dos campos. Um excesso horizontal do formulário foi identificado e corrigido com coluna responsiva e `min-width: 0`; dados e serviços de homologação não foram usados.
- Não há evidência de ciclo red/green de todos os testes novos antes do código; por isso 1.3 permanece aberta em sua redação estrita. Regressões funcionais estão implementadas e validadas. Em 2.1, somente a persistência PIX está entregue; recibo de exclusão de cliente permanece pendente.

## Limite de entrega e homologação

O inventário zero-impact confirmou o projeto Compose `markina-gallery`, arquivo `docker/docker-compose.yml`, web interno 3000, API interna 8000 e somente o Nginx publicado em `127.0.0.1:8080` no subdomínio existente `markina-homolog.duckdns.org`; nenhuma porta, DNS, certificado, proxy ou recurso de terceiro foi criado ou alterado. Rollback preserva schema aditivo, configuração anterior e backups lógicos restritos da Markina.

Após autorização explícita, o run `34073273777` publicou a implementação funcional e executou a limpeza autorizada de galerias/clientes de teste depois de backup lógico, preservando administrador, configurações e pareamento WhatsApp. O inventário posterior confirmou zero clientes, galerias, fotos, pedidos, vínculos, seleções e arquivos de mídia. Uma falha segura de ativação facial por resolução interna antiga do Nginx foi corrigida sem alcançar outros projetos.

O run corretivo `34073819354` terminou verde e publicou o SHA funcional `07aa6dffdcbeb70e3a0f7eba91cc66dfaa150961` nos deployments `6300430858` e `6300438039`. O servidor confirmou migration `20260906_0046 (head)`, API/web/workers saudáveis, piloto facial sintético adulto ativo, menores desligados e somente `127.0.0.1:8080` publicado. Em 2026-09-07 UTC, `/healthz` respondeu `200 ok` e `/api/health` respondeu `200 {"status":"ok","service":"api"}`. O diretório permaneceu vazio após o deploy corretivo. A revisão autenticada do PIX global em desktop/mobile de homologação continua humana e impede concluir 7.6, mas não impede a paridade funcional do código publicado.

Tarefas de diretório/lifecycle de clientes e teste de exclusão continuam fora do escopo PIX priorizado. Não sincronizar specs consolidadas nem arquivar a change sem revisão humana.
