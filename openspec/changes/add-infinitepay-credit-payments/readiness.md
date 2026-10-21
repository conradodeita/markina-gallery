# Prontidão e evidências — 12/10/2026

## Correção do baseline

O relatório inicial foi produzido no checkout antigo `feature/improve-individual-selection-download-and-private-layout`, HEAD `95dbab718b5f0b705fa127d86649b308dba8ba36`. Ele não representava a versão atual de develop. Após atualização somente dos refs, a diferença para a versão examinada foi de 141 commits.

Foi criado um worktree separado e limpo a partir de `origin/develop`, SHA `f942cf3a74c432b53263f175c27f5b4274bcae82`, na branch `feature/infinitepay-credit-readiness`. As alterações locais preexistentes da pasta original não foram incorporadas, revertidas ou reformatadas. A análise fixa este SHA verde; uma CI de outro SHA foi observada em execução concorrente e não é evidência deste trabalho.

## PIX já isolado nesta versão

- `backend/app/global_pix.py`: consulta exige conta ativa e filtra `GlobalPixSettings.tenant_id`; escrita confere o vínculo administrativo. Não há resolução de recebedor de outra conta como fallback.
- `backend/app/ownership_schema.py`: a unicidade natural/singleton dos modelos é contextualizada por tenant e relações recebem constraints de owner. O `unique=True` histórico de um campo isolado no modelo não representa sozinho o schema final montado.
- `backend/app/unified_checkout.py`: preparação resolve tenant do cliente, valida recursos de mesma conta e congela PIX próprio; grupos, comunicações, decisões, seleções e histórico são consultados no mesmo escopo.
- O delta vigente em `add-small-multi-photographer-pilot/specs/gallery-sales/global-pix-configuration/spec.md` explicita que global significa conta do fotógrafo, não instalação inteira. A sincronização/aceite dessa change permanece em seu fluxo próprio.

Conclusão verificada: não é necessário reimplementar o isolamento do PIX como pré-requisito novo nesta preparação. A nova integração deverá preservar e testar esses contratos. Isto não conclui homologação A/B nem revisão da change multitenant.

## Validação reproduzida

Comando executado em `backend/` do SHA examinado, utilizando o runtime Python existente, `APP_ENV=development`, `DATABASE_URL` de SQLite sintético próprio fora do Git e sem `PHOTOGRAPHER_TEST_DATABASE_URL`:

```text
python -m pytest tests/test_tenant_configuration.py tests/test_tenant_commerce.py -q --basetemp <diretório sintético próprio> --junitxml <XML fora do Git>
```

Resultado: **28 passed, 0 skipped, 6 warnings em 99,66 s**. As advertências são de depreciação `on_event` do FastAPI, já existentes. As fixtures usam duas contas, mesmo telefone com identidades independentes, PIX/valores distintos e fronteiras externas sintéticas. Cobrem leitura/alteração PIX, desafio estrangeiro/vínculo revogado, snapshots, carrinho misto, compras/decisões/histórico e recursos cruzados.

Limite: esta reexecução foi em SQLite; Docker Desktop estava indisponível. Nenhum daemon/serviço/contêiner foi iniciado, modificado ou removido. Não atribuir validação PostgreSQL local a esta execução. XML e bancos temporários ficam fora do repositório; não versionar paths de artefatos locais como dependência do próximo executor.

## CI da base exata

[CI 38241570425](https://github.com/conradodeita/markina-gallery/actions/runs/38241570425), SHA `f942cf3a74c432b53263f175c27f5b4274bcae82`, concluída com sucesso em 12/10/2026. Jobs backend, frontend, OpenSpec, Gitleaks, Gemma runtime e deploy-homolog constam como success. O log do job backend `114785185214` registra **1.346 passed, 20 skipped em 1.380,79 s**, seguido de **1 passed** na verificação separada. A configuração do job inclui PostgreSQL sintético específico para fotógrafos; o resumo agregado não transforma casos skipped em aprovados.

Essa evidência foi lida, não disparada por este executor. Não autoriza deploy novo, prova de recebimento bancário nem ativação de InfinitePay.

## Inspeção da interface existente

Leitura autenticada via aba Chrome autorizada em `https://markina-homolog.duckdns.org/admin/settings`. A seção PIX está apresentada como `Pagamentos · Sua conta`, com edição sensível e configuração existente. Nenhum formulário foi preenchido/salvo, recebedor alterado, transação criada ou ação financeira executada. Dados do recebedor/QR e credenciais não foram copiados para este artefato.

Limite: uma sessão de fotógrafo não comprova isolamento remoto de duas contas nem informa SHA/schema do servidor. A prova de propriedade está no código/testes da base e no fluxo de homologação A/B da change correspondente.

## Dependências e limites de prontidão

| Identificador | Estado | Consequência |
|---|---|---|
| D1 — isolamento/piloto | Implementação local e CI da base disponíveis. `add-small-multi-photographer-pilot` ainda contém tarefas remotas/revisão desmarcadas e registros históricos de publicação. Não concluir nem reexecutar esses passos silenciosamente. | Antes de aplicar esta change, reconciliar estado/evidências da dependência e registrar quais gates permitem preparação local; operação multitenant real exige seu aceite próprio. |
| D2 — proposta InfinitePay | Os artefatos desta change são planejamento ainda sem aceite de implementação. | Próximo executor deve obter/reconhecer a revisão do contrato antes de alterar código. |
| G1–G5 — contrato externo | Pendentes conforme `provider-contract.md`. | Bloqueiam as implementações dependentes de garantias presumidas e a ativação real, sem bloquear preparação local independente após aceite. |
| Operação real | Sem conta de provedor/ambiente de teste verificados, autorização de configuração externa, pagamento ou deploy desta change. | Preparar pacote exato antes de solicitar autorizações; não usar dinheiro real para avaliar esta proposta. |

## Estado desta entrega

Registro histórico da preparação inicial. A continuação em `implementation.md` agora acrescenta o cliente HTTP local/mockado para o contrato público; nenhum checkout foi emitido pelo backend, nenhuma chave foi configurada e nenhum pagamento real foi feito. Código de PIX e specs principais não foram alterados. G1–G5 e D1/D2 continuam explícitos.

## Estado após implementação local — 12/10/2026

A autorização posterior do titular aceitou prosseguir sem API Key e testar com a própria conta. A aplicação local já contém a seleção PIX/cartão, configuração individual por InfiniteTag/autodeclaração, reserva e emissão idempotente do link por `POST /links`, retorno por `order_nsu` UUID e confirmação por `payment_check`. O meio PIX existente não é enviado ao provider e mantém confirmação manual. A API Key não é coletada nem persistida porque seu contrato para esta chamada não está documentado e o proprietário autorizou este perfil sem chave.

Validação local mais recente: 26 testes do adaptador HTTP passaram; 4 casos direcionados de rota/retorno passaram; 19 testes do carrinho e painel passaram; TypeScript, build Next, Ruff, `py_compile`, inventory ownership e OpenSpec estrito passaram (95/95). Lint frontend passou sem erros e com avisos existentes. Nenhum desses resultados constitui homologação InfinitePay. Gitleaks não está instalado no ambiente local; CI exige essa verificação antes do job de deploy.

Ainda faltam: pacote operacional com versão imutável; autorização explícita para publicar a homologação (push em `develop` aciona deploy automático); configuração autenticada do Checkout Integrado pelo titular; conferência do recebedor/cartão sem PIX no link; ensaio com compra real e verificação `/payment_check`. Não há API Key em configuração do Pick-your-Pic, checkout ou pagamento efetuado. A InfiniteTag fornecida em conversa não está gravada no repositório.

Limites mantidos: sem webhook até documentar assinatura e autenticação; pagamentos sem retorno permanecem para conciliação, sem confirmação ou liberação de fotos. O texto/relato do titular sobre PIX desligado é registrado como orientação de configuração, mas a visualização de link API sem PIX ainda precisa ser verificada antes de aceitar pagamentos.

## Plano de homologação preparado — ainda não executado

- **Versão:** worktree `feature/infinitepay-credit-readiness` baseado em `c17b9e0d991bdc82199c0c0e10a6220928a5d6c2`; diff ainda sem commit/SHA imutável. Schema anterior `20261012_0077`, então migrations de `develop` `20261014_0078`/`0079` foram integradas e a nova revisão será `20261014_0080`. O deploy não pode apontar para este worktree sujo; será necessário aprovar e promover um commit revisado para `develop`.
- **Automação:** `.github/workflows/ci.yml` executa deploy-homolog somente em push a `develop`, após backend, frontend, Gemma runtime, OpenSpec e Gitleaks. Não houve push/PR/merge ou deploy.
- **Alvo declarado na configuração:** projeto Compose `markina-gallery`, arquivo `docker/docker-compose.yml`, homolog `https://markina-homolog.duckdns.org`. Única porta publicada por esse Compose é Nginx `${MARKINA_GALLERY_PORT:-8080}:80` (8080 padrão); API/web/DB/Redis são internos. A stack conecta-se a redes e proxy existentes, que não serão alterados fora dos serviços do projeto.
- **Impacto e preflight:** workflow/script limitam o checkout a `/opt/markina-gallery`, verificam repositório e checkout limpo, coletam SHA/schema anterior, fazem `pg_dump` lógico próprio em `/var/lib/markina-gallery/backups` e escrevem manifest antes de trocar o SHA. Após migrations verificam revisão Alembic e healthchecks internos e públicos. Nenhum serviço/projeto vizinho deve ser reiniciado ou modificado.
- **Migrations:** 0075–0077 adicionam configuração/tabelas e histórico; `20261014_0078` e `0079` pertencem a mudanças já integradas em `develop`; `20261014_0080` adiciona a coluna de disponibilidade de cartão. Seu downgrade recusa remover preferências habilitadas. Depois que uma migration altera schema, o deploy script não faz rollback automático do código nem restaura DB: exige manter dados e corrigir para frente ou plano humano de restauração a partir do backup. Validar o estado remoto e ensaiar contingência no preflight antes de autorizar. A coluna `card_enabled` inicia falsa para registros existentes; o fotógrafo deverá habilitar o cartão explicitamente em Configurações após o deploy.
- **Janela e reversão:** janela e acompanhamento humano a combinar antes da autorização. Se falhar antes de mudança de schema, o script pode restaurar somente o código; depois de schema avançado, não executar downgrade nem restaurar automaticamente. Preservar pagamentos pendentes e confirmar healthchecks/retorno ao SHA saudável via processo controlado.

O escopo foi revisado e registrado em Conventional Commit `e9274d994800950e7f30a43435bb484973241cb5`. O branch foi atualizado sem conflito com `origin/develop` `ef6dc99df21ef72d9f610c564a451f85390ac4e8`, por merge `23908137036204440cc6315bf4a2484c5a806304`; a árvore está limpa e esse commit incorpora a atualização documental mais recente de `develop`. O SHA de pacote para CI será o HEAD final depois desta atualização de prontidão. Tarefas 6.2–6.4 permanecem pendentes; a publicação está autorizada pelo titular, mas ainda não foi iniciada.

## Correções após a CI do PR — 13/10/2026

## Complemento de disponibilidade explícita e tentativa sem URL — 13/10/2026

O proprietário pediu um controle por fotógrafo para ligar/desligar a oferta de cartão. A revisão local acrescenta `card_enabled`, migration aditiva inicialmente planejada como `20261013_0078` e agora renumerada para `20261014_0080` após integrar migrations mais recentes de `develop`. O estado desligado bloqueia somente novos checkouts. O valor padrão é falso, portanto configurações antigas não ativarão automaticamente o novo campo. Links pendentes permanecem retomáveis, inclusive após desligar a oferta para novas compras.

Na página de cliente, a compra de R$ 0,10 e uma tentativa anterior aparecem como `verification_required` sem link de checkout; o pedido de R$ 7,00 permanece com link para continuar. O proprietário afirma que o gateway não abriu e que nenhum pagamento foi concluído. A resposta HTTP original não foi registrada pelo backend, logo não se sabe se a API recusou por valor mínimo, houve falha de rede ou resposta inválida. A mensagem de cliente foi ajustada para diferenciar ausência de URL utilizável de pagamento confirmado. Não alterar estado financeiro nem liberar seleções sem evidência; não inferir limite mínimo da InfinitePay.

Validação local após a pergunta sobre prontidão de push — 13/10/2026: opção implementada localmente na worktree `feature/infinitepay-credit-readiness`. Painel/checkout: 32 testes frontend passaram; testes backend focados de configuração/checkout: 33 passaram e 1 foi ignorado; Ruff, TypeScript, build Next.js e `git diff --check` passaram. ESLint passou sem erros, com 37 avisos no total. `openspec validate add-infinitepay-credit-payments --type change --strict --no-interactive --json` passou sem issues. Uma execução backend mais ampla parou em `test_upgrade_e_downgrade_vazios_preservam_compras`: a fixture usa SQLite, mas a migration 0070 exige PostgreSQL. `DATABASE_URL` não está configurada neste host, então a migration 0078 não foi ensaiada localmente em PostgreSQL. Não houve alteração de pedido/configuração real, commit ou deploy. As tasks 2.4, 5.4 e 5.5 continuam pendentes de validação e reconciliação; a causa original da resposta sem URL não foi obtida e não pode ser declarada corrigida.

Investigação adicional do motivo da tentativa sem checkout — 13/10/2026: `InfinitePayHttpProvider.create_checkout` reduz respostas não-2xx, resposta ausente, JSON inválido e URL inválida a `outcome=unknown`/`invalid_response`; exceções de transporte também são normalizadas. `issue_provider_payment` grava antes da chamada externa o estado durável `verification_required` e `transport_unknown`; não persiste status HTTP nem corpo externo e não tenta novamente. Assim, o registro atual não contém a informação necessária para reconstruir qual desses casos ocorreu. A documentação oficial atual confirma `POST /links` e exemplo de retorno `url`, mas não descreve valor mínimo nem semântica de erro que permita concluir por que R$ 0,10 não gerou um link: https://www.infinitepay.io/checkout-documentacao. Atribuir a falha ao valor de R$ 0,10 seria especulação. A task 6.6 segue bloqueada até haver log externo correspondente ou diagnóstico autorizado em tentativa isolada após conciliação.

A CI `38336262062` do HEAD `2d6a5867d721ca36a093a726bc3481318e6faf40` aprovou frontend, OpenSpec, Gitleaks e Gemma runtime, mas o backend falhou em dois testes (1.464 passaram, 20 foram pulados):

- `test_clique_concorrente_com_mesma_chave_produz_uma_reserva` concorria em SQLite, cujo dialeto ignora `SELECT ... FOR UPDATE`; isso permite colisão na constraint única e não simula a serialização de checkout suportada por PostgreSQL. O teste agora pula explicitamente em SQLite; a CI acrescenta uma execução direcionada com `DATABASE_URL` no PostgreSQL de teste, e a fixture semeia o tenant sintético exigido por esse caminho. Não declarar a propriedade concorrente validada somente pelo skip SQLite.
- `test_limpeza_preserva_admin_conta_sessao_e_canal[postgresql]` migrava apenas até `20261011_0074`, mas validava o catálogo atual, que inclui configurações/tabelas adicionadas nas revisions 0075–0077. A fixture foi alinhada à revision `20261012_0077` para que o teste percorra o schema corrente e verifique as cinco tabelas InfinityPay/provider.

Validação local pós-correção: `python -m pytest tests/test_provider_checkout.py tests/test_tenant_migration.py::test_limpeza_preserva_admin_conta_sessao_e_canal -q` — **18 passaram, 3 foram pulados em 143,80 s**; os skips de migração PostgreSQL indicam que este host não forneceu a URL PostgreSQL do ensaio. `ruff check app tests` passou; OpenSpec da change estrito e `git diff --check` passaram. Essa validação não substitui a reexecução completa do backend PostgreSQL/GitHub Actions. Novo CI e todos os seus checks verdes continuam como gate antes do merge/deploy.

Validação executada com a versão de CLI fixada pela CI, `@fission-ai/openspec@1.14.0`:

```text
npx --yes @fission-ai/openspec@1.14.0 validate add-infinitepay-credit-payments --type change --strict --no-interactive --json
npx --yes @fission-ai/openspec@1.14.0 validate --strict --all --no-interactive --json
npx --yes @fission-ai/openspec@1.14.0 status --change add-infinitepay-credit-payments
git diff --check
```

Resultado: change válida sem issues; validação geral **95/95** (76 changes e 19 specs); quatro artefatos requeridos presentes. O delta possui 12 requisitos e 26 cenários, com descrições normativas de até 500 caracteres. Revisão dos arquivos e diff confirmou sete arquivos novos exclusivamente desta change, nenhum diff de runtime/spec principal e ausência de erros de whitespace. O planejamento não altera a exigência arquitetural de assinatura nem preenche gates com hipóteses. Tarefas 1.1–1.3 concluídas como preparação; tarefas de aplicação e gates permanecem pendentes.

## Retomada segura, disponibilidade explícita e situação do rollout — 13/10/2026

O proprietário decidiu que uma cliente somente poderá tentar novamente as mesmas fotos após confirmação de que o link de checkout não foi criado. Essa orientação confirma a regra já codificada: `failed_before_issue/not_created` restaura a seleção e permite nova chave; `verification_required` não oferece cartão ou PIX alternativo e conserva a reserva, mesmo quando a cliente diz que não chegou a abrir o gateway.

O painel agora permite ligar/desligar novos pagamentos com cartão sob o desafio sensível da conta. A migration aditiva 0080 inicia a preferência como desligada. Testes sintéticos em `backend/tests/test_provider_payment_correction_migration.py` verificam default falso e preservação do registro contra downgrade destrutivo; aguardam execução PostgreSQL na CI. `frontend/`: configuração, carrinho e compras — **37 testes passaram**; `npx tsc --noEmit` passou. `backend/`: configuração tenant e rota de cartão/replay — **16 testes passaram, 7 avisos**. O teste garante que cartão desligado bloqueia novos checkouts sem remover URL/tentativa emitida. Ruff, build e OpenSpec devem ser repetidos no SHA revisado.

A tentativa antiga de R$ 0,10 permanece em `verification_required`. A evidência atual confirma ausência de URL no aplicativo e que o comprador não viu o gateway; não confirma se `/links` criou algum destino remoto. O proprietário decidiu que só deve haver nova emissão das mesmas fotos após confirmação de que o link não foi criado. Manter o gate 6.6 pendente; não limpar/liberar/reemitir essas fotos. A migration 0080 é aditiva e mantém cartão desligado por padrão; a publicação não altera a tentativa incerta nem habilita novas cobranças. Com autorização do proprietário para push/merge/deploy e preservação desse estado, o gate 6.6 bloqueia a recuperação daquela seleção, não uma publicação inativa nem um ensaio posterior com fotos distintas.

## Rebase por merge de `develop` e colisão de Alembic — 13/10/2026

Antes de enviar o branch, foi atualizado `origin/develop` e integrado por merge normal, sem descartar ou reformatar alterações existentes. `develop` já havia ocupado revisions `20261014_0078` (RAW) e `20261014_0079` (processamento de pasta pública); por isso, a revisão inicialmente local para cartão conflitou com 0078. A mudança foi corrigida para `20261014_0080`, com `down_revision=20261014_0079`, e os testes que apontam para schema corrente foram atualizados para 0080. Os conflitos em `test_tenant_migration.py` e `test_tenant_photographer_migration.py` foram resolvidos para continuar migrando até o schema consolidado 0080. A CI PostgreSQL #38405667260 aprovou a migration 0080 e os testes históricos no SHA `e6ff2c8837c2337906fdf53a5daca1c9d405d2d9`; task 2.4 concluída.

O primeiro run completo da CI no PR #166 teve `frontend`, `gemma-runtime`, `gitleaks` e `openspec` aprovados. Backend PostgreSQL executou **1.518 aprovados, 21 ignorados** e falhou em um teste histórico: `test_tenant_infinitepay_migration.py::test_downgrade_recusa_configuracao_existente` tentou persistir a coluna nova usando o ORM atual enquanto a migration estava no schema 0075. A fixture foi corrigida para refletir as colunas históricas. No run #38405667260, backend PostgreSQL concluiu com **1.520 aprovados, 21 ignorados** e as três regressões adicionais passaram; frontend, OpenSpec, Gitleaks e runtime Gemma também passaram. O deploy-homolog foi pulado no evento de pull request. Esta evidência conclui a task 2.4, mas não substitui ensaio da conta InfinitePay ou deploy.

## Evidência para promoção da versão — 13/10/2026

O código está no PR #166, head `e6ff2c8837c2337906fdf53a5daca1c9d405d2d9`, target `develop`. O usuário autorizou push/merge/deploy para homologação. O alvo configurado é `https://markina-homolog.duckdns.org`; projeto Compose `markina-gallery`, arquivo `docker/docker-compose.yml`, Nginx publicado em `8080:80` por padrão e serviços internos. O workflow de deploy opera apenas no checkout `/opt/markina-gallery`, salva backup lógico e manifest, verifica o SHA/schema e healthchecks; não modifica serviços de projetos vizinhos. A migration 0080 é aditiva e inicia `card_enabled=false`; depois do avanço de schema, não há downgrade/rollback automático de banco. O CI de PR pulou deploy-homolog, que só é disparado por push a `develop`.

O gate de reconciliação da tentativa de R$ 0,10 continua separado: não alterar seu estado `verification_required`, não reemitir e não liberar as fotos sem prova de que não houve criação do link. A publicação inicial deixa cartão desativado por padrão e não repete chamadas externas. Qualquer ensaio após publicar precisa usar um pedido e fotos diferentes. O ensaio real e a habilitação da conta ainda dependem da configuração pelo titular e serão registrados como pendentes até ocorrerem.

## Preservação do estado dos módulos fora do escopo — 13/10/2026

O proprietário escolheu preservar o estado atual de processamento facial e desenvolvimento RAW para esta publicação. A inspeção encontrou que o workflow de homologação forçava ambos como `true`. A correção remove esses overrides: facial permanece conforme `FACIAL_PROCESSING_ENABLED` persistido no `.env.homolog`; RAW passa ao modo automático, que detecta o worker `raw-development-worker` ativo no projeto e só o inclui/atualiza quando já estava ativo. Se estiver inativo, o deploy não o inicia.

Validação: `bash scripts/test_deploy_homolog.sh` passou no Git Bash do Windows, incluindo as verificações do workflow e os casos sintéticos de facial/RAW; `python scripts/test_deploy_homolog_policy.py` passou isoladamente; OpenSpec estrito passou (1/1); `git diff --check` passou. Essa correção está pronta para CI no PR; não executou deploy.

## Incidente de produção e plano de release API/web — 20/10/2026

Inventário remoto, somente leitura: domínio `https://markina.pickyourpic.com.br`; Compose `markina-gallery` com arquivo-base `/opt/markina-gallery/docker/docker-compose.yml` e overlays de branding, RAW, ajuste de prévias e monitoramento; API `markina-gallery-api-1`, `APP_VERSION=fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`, imagem `sha256:afc54e0ff0b008ac7bcc2ab28095f279da6213aaa5bec1ac98fae8269fc0715c`; web `markina-gallery-web-1`, imagem `sha256:768698a20b7042cf63a6e56df74fdea18a8e86b7086bbaa6c5bb8ba79d59250d`; schema PostgreSQL `20261017_0084 (head)`. Nginx Markina publica internamente `127.0.0.1:8080->80`; o proxy compartilhado mantém as portas públicas 80/443. Os containers estavam saudáveis no inventário inicial. Nenhuma imagem, container, dado, migration ou serviço foi alterado.

Escopo desta correção: `backend/app/payment_provider.py` e `backend/app/provider_checkout.py`, ambos runtime da API. Nenhuma dependência, frontend, worker, schema, migration ou Compose mudou. O classificador oficial só permite os hashes runtime listados; `scripts/check_prod_app_release_scope.py` e `openspec/changes/add-production-app-release-workflow/runtime-gates.json` foram preparados para incluir exatamente os dois blobs alterados. O gate unitário do classificador passou 11 testes. A versão de schema exigida pelo release permanece 0084.

Procedimento preparado, sem execução: PR/CI verde em `main`; preflight oficial inventaria somente API/web e fixa SHA, imagens e lock; após autorização operacional independente, o workflow oficial compila imagens e recria `api` e `web` com `--force-recreate --wait`, valida healthchecks, testa/recarrega somente o Nginx Markina e verifica HTTPS em `/healthz`, `/api/health` e `/`. O serviço API é necessário para esta alteração; o workflow existente também recria web mesmo sem mudança de frontend, o que pode causar breve interrupção e exige janela operacional. O rollback oficial `app-rollback` restaura IDs de imagem anteriores e `APP_VERSION`, valida healthchecks e smoke HTTPS; é código-only porque esta alteração não tem migration. O plano não usa release Python, não altera outros projetos e não publica automaticamente a partir deste branch.

GO/NO-GO atual: **NO-GO para recuperação da compra e para publicação emergencial**. A compra está financeiramente desconhecida no provedor; a resposta original não foi preservada; a documentação vigente pede `X-Api-Key` em `payment_check` e o fluxo atual não envia chave; homologação e ensaio externo não foram executados. Menor próximo passo do titular: consultar InfinitePay pelo `order_nsu` e confirmar se o link foi criado/pago; em paralelo, obter esclarecimento oficial sobre autenticação e definir armazenamento seguro de chave por fotógrafo. Não liberar nem reemitir a compra durante essa pendência.

Validação final desta correção: `pytest tests/test_infinitepay_http_provider.py tests/test_provider_checkout.py -q --disable-warnings --maxfail=1` — **48 passaram, 1 ignorado** (teste PostgreSQL concorrente indisponível neste host); `ruff check` nos módulos/testes alterados, `python -m py_compile` e `git diff --check` passaram. `python scripts/test_prod_app_release_scope.py` — **11 passaram**. `@fission-ai/openspec@1.14.0 validate add-infinitepay-credit-payments --type change --strict --no-interactive --json` — **válida**; validação estrita completa — **130/130** (108 changes e 22 specs). CI PostgreSQL continua gate antes de merge. Nenhuma validação executou chamada de checkout real.

Revisão complementar das fontes oficiais em 20/10/2026 está registrada em `provider-contract.md`: o payload básico de criação permanece compatível com o contrato interativo legado, enquanto a Central de Ajuda atual é contraditória sobre exigir chave em `/links`; para `/payment_check`, ela mostra `X-Api-Key` e o cliente atual não envia o header. O estado original não registra o status HTTP, portanto essa diferença não prova a causa da falha de abertura. As opções avançadas de link documentam cartão e PIX juntos, mas exigem chave conforme a página e a confirmação local de cartão rejeita `capture_method=pix`; não habilitar esse modo sem definição de segredo por fotógrafo e contrato de receita. A documentação lista eventos webhook, mas não sua autenticação/assinatura. `payment_check` público requer `transaction_nsu` e `slug`, então não fornece sozinho reconciliação por `order_nsu` após resposta perdida. O CI #750 ainda está em execução no job backend na última consulta; os demais jobs concluíram com sucesso. Nenhuma alteração do contrato foi presumida.

## Contrato autenticado, binding e CI #750 concluído — 20/10/2026

Resultado final do CI #750: run `39513983428` concluiu com sucesso no SHA anterior `b786862bb6619fc0e6825d73e1849d58da1420e1`. Backend: **1.711 aprovados, 23 ignorados**, mais regressões PostgreSQL multi-tenant **4**, checkout concorrente **1** e inventário de exclusão **1**, todas aprovadas. Frontend, OpenSpec, Gitleaks, Gemma runtime e runtime-images passaram; deploy/preflight foram pulados no PR. Esse CI não contém o binding e as alterações desta revisão; após atualização do mesmo PR draft, a nova revisão deverá passar seu próprio CI.

Contrato revalidado na Central de Ajuda e documentação interativa oficial: criação básica `/links` pode não usar chave; opções avançadas (crédito exclusivo/link único) pedem `X-Api-Key`; `payment_check` também documenta o header. Isso confirma a incompatibilidade de autenticação da consulta existente, não prova a causa da tentativa sem URL. Código preparado para binding único por tenant/ambiente em configuração server-side injetada somente na API; nenhum segredo real foi consultado ou gravado. Os dados do cofre/conta ainda não foram provisionados e a UI informa que o cartão aguarda vínculo.

O fluxo integrado de PIX foi mantido fora da mudança porque o agregado e a confirmação financeira atuais aceitam somente cartão; PIX manual continua disponível quando configurado. Resultado HTTP ambíguo mantém reservas e bloqueia troca de meio. A recuperação automática só ocorre com resultado tipado `not_created`; a tentativa de produção exige busca manual da InfinitePay por `order_nsu`, confirmação de ausência de checkout ativo e ausência de pagamento, seguida de autorização expressa do proprietário para qualquer recuperação. Não atualizar `e2194ce5` com esta confirmação documental.

## Binding e validação local concluídos — 20/10/2026

O código e a documentação do binding por tenant estão preparados para revisão no PR draft. O fotógrafo não recebe uma interface para cadastrar API Key: o repositório não contém um cofre acessível ao proprietário; o binding só lê configuração segura injetada no serviço API. O proprietário possui uma chave, mas nenhum valor foi solicitado, recebido ou armazenado. Publicação requer provisionamento operacional seguro e ensaio autorizado de checkout no ambiente apropriado.

Testes locais focados: **122 aprovados, 3 ignorados, 46 avisos**; frontend do painel **8 aprovados**, TypeScript, ESLint, Ruff, `py_compile`, Compose config, `git diff --check`, 12 testes do classificador de release e validação estrita desta change OpenSpec passaram. A validação global estrita ainda falha em 31 itens de outras changes/specs; não foram modificados neste trabalho. CI #750 passou no SHA anterior à implementação do binding; a revisão atual precisa de novo CI completo antes de considerar apta para solicitar autorização de publicação.

GO/NO-GO: **GO para solicitar revisão do PR draft após o CI da nova revisão ficar verde; NO-GO para publicação até o provisionamento seguro da chave e ensaio autorizado; NO-GO para recuperar `e2194ce5` até a InfinitePay confirmar por `order_nsu` o estado do checkout e do pagamento e o proprietário autorizar explicitamente qualquer ação.** Nenhum deploy, merge, alteração da compra ou chamada financeira real foi executado.
