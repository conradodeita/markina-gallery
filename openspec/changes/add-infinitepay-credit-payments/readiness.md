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

- **Versão:** worktree `feature/infinitepay-credit-readiness` baseado em `c17b9e0d991bdc82199c0c0e10a6220928a5d6c2`; diff ainda sem commit/SHA imutável. Schema alvo `20261012_0077`. O deploy não pode apontar para este worktree sujo; será necessário aprovar e promover um commit revisado para `develop`.
- **Automação:** `.github/workflows/ci.yml` executa deploy-homolog somente em push a `develop`, após backend, frontend, Gemma runtime, OpenSpec e Gitleaks. Não houve push/PR/merge ou deploy.
- **Alvo declarado na configuração:** projeto Compose `markina-gallery`, arquivo `docker/docker-compose.yml`, homolog `https://markina-homolog.duckdns.org`. Única porta publicada por esse Compose é Nginx `${MARKINA_GALLERY_PORT:-8080}:80` (8080 padrão); API/web/DB/Redis são internos. A stack conecta-se a redes e proxy existentes, que não serão alterados fora dos serviços do projeto.
- **Impacto e preflight:** workflow/script limitam o checkout a `/opt/markina-gallery`, verificam repositório e checkout limpo, coletam SHA/schema anterior, fazem `pg_dump` lógico próprio em `/var/lib/markina-gallery/backups` e escrevem manifest antes de trocar o SHA. Após migrations verificam revisão Alembic e healthchecks internos e públicos. Nenhum serviço/projeto vizinho deve ser reiniciado ou modificado.
- **Migrations:** 0075–0077 adicionam configuração/tabelas/coluna e histórico; downgrades recusam apagar registros. Depois que uma migration altera schema, o deploy script não faz rollback automático do código nem restaura DB: exige manter dados e corrigir para frente ou plano humano de restauração a partir do backup. Validar o estado remoto e ensaiar contingência no preflight antes de autorizar.
- **Janela e reversão:** janela e acompanhamento humano a combinar antes da autorização. Se falhar antes de mudança de schema, o script pode restaurar somente o código; depois de schema avançado, não executar downgrade nem restaurar automaticamente. Preservar pagamentos pendentes e confirmar healthchecks/retorno ao SHA saudável via processo controlado.

O escopo foi revisado e registrado em Conventional Commit `e9274d994800950e7f30a43435bb484973241cb5`. O branch foi atualizado sem conflito com `origin/develop` `ef6dc99df21ef72d9f610c564a451f85390ac4e8`, por merge `23908137036204440cc6315bf4a2484c5a806304`; a árvore está limpa e esse commit incorpora a atualização documental mais recente de `develop`. O SHA de pacote para CI será o HEAD final depois desta atualização de prontidão. Tarefas 6.2–6.4 permanecem pendentes; a publicação está autorizada pelo titular, mas ainda não foi iniciada.

## Correções após a CI do PR — 13/10/2026

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
