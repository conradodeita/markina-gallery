# Evidências

- Base: PR #260 aberto/draft, SHA `0959c64`, sem alteração do branch pai.
- OpenSpec strict: `add-infinitepay-tenant-credentials` válida antes de código.
- Crypto: `pytest tests/test_integration_secrets.py -q` — 14 passed, Ruff aprovado.
- Migration: `PHOTOGRAPHER_TEST_DATABASE_URL` aponta somente a PostgreSQL 17 descartável `127.0.0.1:15470/pyp_photographer_test`, container exclusivo `pyp-infinitepay-credentials-test`, dados em tmpfs. `test_infinitepay_credentials_migration.py` — 2 passed em 32,92 s, incluindo preservação, FKs negativas A/B e recusa de downgrade com ciphertext. Ruff aprovado.
- Gerador estático de ownership: bloqueio da base por `KeyError: RawDevelopmentSettings`, antes de alcançar a tabela nova; classificação específica e integridade estão em `ownership.md`.
- Integração nova PostgreSQL: `test_integration_secrets.py`, `test_infinitepay_credential_management.py`, `test_infinitepay_credential_checkout.py` e `test_infinitepay_credentials_migration.py` — **30 passed em 229,73 s**. Inclui 9 casos de gestão HTTP/CLI, 5 contratos de checkout e concorrência, 14 casos criptográficos e 2 migrations; não usa autorização mockada ou chamada financeira real. CLI: dry-run não modifica, apply exige confirmação explícita, A não recifra B e falha criptográfica reverte a transação inteira sem imprimir valores.
- Frontend: **63 arquivos/566 testes passaram** em 83,50 s; card InfinitePay tem 11 casos. `tsc --noEmit`, lint do card e `npm run build` aprovados. Lint global sem erros, 34 avisos fora do card; build gera as mesmas rotas, sem página nova.
- Cleanup isolado SQLite: **12 passed, 1 skipped** (caso que requer PostgreSQL). Nenhuma limpeza foi executada em ambiente operacional.
- `docker compose -p markina-gallery -f docker/docker-compose.yml config --quiet` aprovado, sem imprimir configuração resolvida nem criar serviços. Arquivo seguro novo é opcional, API somente; não criado nesta missão.
- Ruff global `backend/app backend/tests`, `compileall` dos módulos novos e OpenSpec strict aprovados. Reconsulta oficial somente documental registrada em `provider-contract.md`.
- Inventário estático novamente delimitado em 21/10/2026: mesmo `KeyError: RawDevelopmentSettings` da base. A classificação R/K de `InfinitePayCredential` foi adicionada ao mapa, sem alterar classificações da missão RAW; o relatório global não é declarado aprovado.
- Regressão delimitada: os dois parâmetros do teste da migration histórica 0076 comparavam seu schema congelado ao ORM atual e passaram a exigir indevidamente `credential_id`, introduzido somente em 0085. Reproduzido isoladamente antes da correção: `Extra items in the right set: credential_id`. Expectativa histórica de colunas/FKs de `provider_payment` agora é explícita conforme DDL 0076; a migration histórica não foi modificada. Repetição do arquivo: **3 passed em 72,33 s**.
- Regressões pertinentes PostgreSQL (binding/HTTP/provider/disponibilidade/checkout/confirmação/persistência/migrations/configuração/ownership): execução inicial **184 passed, 2 skipped, 2 failed** em 814,96 s. Únicas falhas foram os dois parâmetros históricos descritos acima; os 3 testes desse arquivo passaram após a correção. Demais 184 resultados permanecem aplicáveis, pois nenhuma implementação financeira mudou depois desse ensaio. Não apresentar essa combinação como uma execução única integralmente verde; o CI do head corrigido é o gate integral.
- Criptografia final: **15 passed em 0,23 s**, acrescentando material mestre de 32 bytes incorreto com key-id correto e recuperação com keyring restaurado. Nenhuma chave gerada em runtime de teste foi salva em fixture, log ou artefato.
- PR próprio draft [#262](https://github.com/conradodeita/markina-gallery/pull/262), criado sobre #260; primeiro head `ccf59ea101f0cdcca2bac8d00f426b457d6bdff0`. Primeiro CI `39538286614`: gitleaks/OpenSpec/frontend/Gemma aprovados na consulta, backend/imagens ainda pendentes; não é aprovação do head corrigido. Resultado final será registrado após conclusão do CI, sem merge ou publicação.
- Primeiro CI cancelado explicitamente após correção local para priorizar o head atualizado; não declarado verde. Head intermediário `5347bba846869271260d40b514b34c0c9efd206e` também ainda não é candidato aprovado.
- Revisão das demais comparações históricas delimitou duas expectativas da migration 0075 (FK futura de 0085) e uma classificação da transição 0070 (tabela futura inexistente). Reproduções: 0075 **2 failed/1 passed**, catálogo 0070 **1 failed** com `NoSuchTableError: infinitepay_credential`. Corrigidas somente as expectativas de teste; schema operacional da fixture atualizado para 0085, preservando a revisão histórica explícita 0070.
- Repetição PostgreSQL de `test_tenant_infinitepay_migration.py` + `test_tenant_photographer_migration.py`: **23 passed em 248,79 s**. Depois, o caso de cleanup foi fortalecido com credencial gerida AES-GCM real/sintética, configuração e compra referenciando-a: repetição **1 passed em 24,50 s**, provando preservação e descriptografia após limpeza. Ruff desses arquivos aprovado. Nenhuma migration histórica foi reescrita; nenhum cleanup operacional foi executado.
- Atualização parcial: teste adicional com resposta de API anterior sem flag de capacidade falhou antes da correção (campo secreto habilitado), e passou após exigir `credential_storage_available=true` para coleta/envio/substituição. **12 testes do card**, TypeScript, lint e novo build passaram. Plano exige todas as instâncias API primeiro e barreira de escritas durante troca/rollback.
- Repetição frontend com build em paralelo: **566 passed/1 failed** (567 casos). Única falha em `auth-entry.test.tsx:178`: heading já renderizado antes do efeito de `apple-touch-icon`; arquivo fora do diff. Repetição isolada sem build: **27 passed em 3,40 s**. Não alterar esse outro fluxo nesta missão; repetir suíte sem concorrência de build e exigir CI final verde.
- Repetição integral frontend sem build concorrente: **63 arquivos/567 testes passaram em 68,70 s**. Nenhuma alteração no arquivo de autenticação; os resultados do card, TypeScript, lint e build se mantêm aprovados. Versão final do card: 12 testes.

## Retomada para conclusão — 21/10/2026

- CI integral do head `de582d5bdd510f0e95c8e0ed1f21f9fc98ce31e2`, [39540544153](https://github.com/conradodeita/markina-gallery/actions/runs/39540544153): **4 failed, 1747 passed, 24 skipped** no backend; frontend/Gemma/OpenSpec/gitleaks aprovados. Falhas delimitadas: fixture de cleanup operacional na revisão 0081 sem nova tabela e 3 testes de reset interrompidos por tabela não classificada. Política agregada recusou corretamente.
- Job de imagens não aprovado: log de ARM64 registra `qemu: uncaught target signal 4 (Illegal instruction)` durante `npm ci`, seguido de cancelamento pelo limite de 30 minutos. Alteração preparada e revisada usa matriz nativa AMD64/ARM64 com `fail-fast=false`, conferência de uname e o mesmo gate agregado obrigatório. Nenhum build ou cobertura foi removido. Runner padrão `ubuntu-24.04-arm`, gratuito para repositório público, conforme [GitHub](https://docs.github.com/en/actions/reference/runners/github-hosted-runners); visibilidade PUBLIC confirmada. Não introduz custo pago, mudança de Dockerfile/dependências ou alteração operacional.
- Correções: `infinitepay_credential` em `reset_homolog_owner.TENANT_CONFIG`, preservação por tenant e todas as versões do proprietário, fixture operacional 0085 (ensaios históricos da fundação continuam 0069). Testes agora semeiam 6 envelopes AES-GCM sintéticos em 5 tenants, conferem bytes/referência próprios inalterados, remoção dos 4 tenants elegíveis, recusa antes de mutação e relatório sem valores secretos.
- Repetição direcionada nesta retomada: `test_tenant_owner_reset.py` + `test_tenant_migration.py` — **18 passed, 2 skipped em 148,69 s**. Skips: symlink sem privilégio no Windows (exercitado pelo CI Linux) e variante SQLite do cleanup exclusivo PostgreSQL. Nenhuma operação de reset/limpeza foi executada fora dos schemas/bancos sintéticos descartáveis.
- Ruff global backend e arquivos de scripts alterados aprovado; `compileall` dos scripts aprovado. Políticas `scripts.test_check_ci_results`, `scripts.test_classify_ci_scope`, `scripts.test_python_security_release` — **45 testes passaram**. OpenSpec strict e `git diff --check` aprovados. Validações financeiras/cripto/UI anteriores permanecem aplicáveis; implementações não alteradas nesta retomada.
- Revisão de segurança final limitada às fronteiras #260/#262 registrada em `review.md`. Plano detalhado em `release-plan.md` exige inventário atual, backup/restauração, autorização separada para migration e recuperação por imagem compatível/digest; nada executado na Oracle. Compra `e2194ce5` e PR #261 permanecem intocados. CI integral do próximo head continua pendente; não declarar prontidão até sua conclusão.

## Resultado integral aprovado

Commit de implementação/correções `8465c57d265ed8add463ebf9841b20285fcff4fc`; [CI 39545805272](https://github.com/conradodeita/markina-gallery/actions/runs/39545805272) concluído com **success**, sem job obrigatório pendente ou cancelado:

| Gate | Resultado observado nos logs |
|---|---|
| Backend completo | **1751 passed, 24 skipped**, 1917,15 s; quatro falhas anteriores corrigidas |
| Concorrência multi-tenant PostgreSQL | **4 passed** |
| Checkout concorrente PostgreSQL | **1 passed** |
| Cofre, snapshots e migration PostgreSQL | **16 passed**, 52,27 s |
| Inventário de exclusão PostgreSQL | **1 passed** |
| Frontend | **63 arquivos/567 testes passaram**, lint/build aprovados |
| Imagens nativas | Jobs AMD64 e ARM64 **success**, incluída conferência de versões frontend no lockfile |
| Gemma | **success**, inferência sintética offline |
| OpenSpec | **131 passed, 0 failed** |
| Gitleaks | **success**, histórico completo |
| Política agregadora | **success**, mensagem `All required and applicable CI validations succeeded.` |

Os jobs de release/deploy foram **skipped**, como esperado em PR, e não contam como publicação. Nenhuma operação Oracle ou dado financeiro real foi alterado. PR #260 continua no SHA base e não foi modificado. As tarefas de implementação foram encerradas com essa evidência; sincronização de specs principais e arquivo continuam sujeitos à revisão humana.

O commit subsequente registra somente encerramento documental, sem alterar código/testes/workflows/dependências. O CI do head documental será conferido antes da resposta final; seu link/SHA/resultados serão adicionados ao corpo do PR #262, evitando afirmar aprovação de head não verificado ou gerar commits recursivos apenas para citar o próprio SHA.

## Retomada após o release de pagamentos — planejamento de integração

Verificação atual do head c0746a7: todos os checks obrigatórios concluídos success, inclusive runtimes AMD64/ARM64 nativos; PR #262 aberto/draft contra feature/fix-infinitepay-checkout. A worktree está limpa nesse head e o fetch autorizado obteve main 21b89c3. AGENTS.md, INSTRUCOES_EXECUTOR_CLAUDE_CODE.md, ROADMAP_ARQUITETURA.md e openspec/config.yaml não têm diff entre as bases; as leituras obrigatórias anteriores continuam aplicáveis. Proposal/design/deltas/tasks e os runbooks desta change foram relidos antes de alteração de código.

O release anterior de #263/#265 já foi concluído e validado; suas evidências são próprias e não comprovam o cofre novo. Tasks 6.1–6.3 delimitam a integração, interação entre recuperação e credencial, correção textual do card e CI do novo candidato. Nenhuma dessas validações futuras é declarada executada neste checkpoint. Nenhuma operação Oracle, compra, credencial real ou publicação do cofre está autorizada nesta retomada.

## Integração local com main 21b89c3 — evidência executada

Recibo documental da recuperação publicada incorporado por cherry-pick `b7f2090e`, depois do merge `a65e962`. A integração6.1 está concluída nesse checkpoint; a correção posterior de mínimo/primeiro clique exige integração e validação adicionais antes da aprovação final.

Merge por histórico, preservando guardas de resposta tardia/recuperação e snapshot de credencial. Único conflito em `.github/workflows/ci.yml` resolvido mantendo tanto PostgreSQL de checkout/reabertura quanto cofre/migration, além de imagens nativas AMD64/ARM64.

Novo teste combinado `test_reopened_cart_preserves_old_credential_and_uses_replacement_for_new_checkout`: resposta HTTP antiga retida, substituição protegida de chave, recuperação das mesmas três fotos, resposta tardia sem regressão e nova compra usando somente a nova credencial. Transporte HTTP sintético, sem pagamento real. Resultado dirigido: **1 passed, 6 warnings, 6,95 s**. Primeira execução encontrou erro de fixture `revision` versus campo público `cart_revision`; corrigido apenas no teste.

Matriz PostgreSQL local `test_provider_cart_recovery.py test_provider_cart_recovery_api.py` + concorrência de checkout + credenciais checkout/gestão/migration + integração de segredos: **77 passed, 7 warnings, 412,26 s**. Log local `C:/codex-data/tmp/vault-main-integration-postgres-15470.log`. Configuração exclusivamente sintética, porta127.0.0.1:15470/banco pyp_photographer_test. A primeira tentativa na porta55458 passou66 e teve11 erros de setup porque fixtures do cofre exigem15470/nome de banco dedicado; nenhum gate foi flexibilizado, a matriz integral foi repetida corretamente.

Ruff backend aprovado, políticas unitárias `check_ci_results`/`classify_ci_scope`16 testes aprovados e OpenSpec1.14.0 global133/0 na árvore integrada deste checkpoint. Gate `test_production_release_workflow_policy.py` ainda recusa os blobs do cofre incompatíveis com o manifesto do release0084 publicado; não foram alterados manifests, allowlists, wrappers ou scripts de release para aprovar cofre. Essa pendência impede declarar CI/release final aprovado e é da task6.3.

O proprietário priorizou também mínimo local de R$1 e redirecionamento no primeiro clique em branch separada `codex/fix-infinitepay-minimum-redirect`. Esta validação77 não inclui essa alteração posterior. Nenhuma operação Oracle, migração, segredo real, compra real ou publicação realizada nesta retomada.

## Orientação do card atualizada

Regressão da orientação por link falhou antes da correção (1failed/12skipped), por ausência do texto esperado. Depois da mudança textual: `npm test -- app/admin/settings/infinitepay-panel.test.tsx --maxWorkers=1` — **13 passed**,3,62s. As opções por link conservam crédito somente; PIX manual continua independente. Sem alteração da coleta transitória, senha/OTP, ownership, opções do adaptador ou ação financeira. Build/lint/suíte completos serão conferidos após integrar também a correção do mínimo/redirecionamento.

## Candidato unificado com mínimo e primeiro clique

Merge local `be3f36e` incorpora o PR#266/heada93dfae por histórico, sem reescrever commits ou substituir snapshots do cofre. Nova guarda mínima precede os efeitos; as duas implementações coexistem. Não inclui código do PR261 nem alteração de dependências em relação à main21.

- PostgreSQL sintético: `test_provider_checkout.py test_infinitepay_credential_checkout.py` — **37 passed,6warnings,291,29s**. Inclui os novos casos abaixo deR$1, fronteira/itens baratos, replay histórico, checkout/retorno com chave original, binding legado, troca concorrente e reabertura com troca de credencial.
- Suíte frontend inteira `npm test -- --maxWorkers=2`: **67arquivos/610testes aprovados**,159,09s. Inclui13casos do card e navegação/PIX/recuperação do carrinho. Não aumentados timeouts ou alterados testes administrativos alheios.
- Lint: **0erros/34avisos preexistentes**. Build e TypeScript **exit0** após a integração; logs locais vault-unified-minimum-redirect-{lint,build}.log.
- Ruff no mesmo escopo do CI, `backend/app backend/tests`, aprovado. Uma execução inadvertidamente mais ampla sobre `backend` alcançou migrations históricas e reportou17 problemas preexistentes; não houve reformat/alteração desses arquivos, e essa execução não é reportada como aprovação.
- OpenSpec na versão do CI1.14.0: **134passed/0failed** após novo delta operacional.

## Correção do teste de política, preservando recusa operacional

O teste original falhava ao comparar o runtime do cofre com pins0084. O verificador/classificador/manifestos/wrappers de produção NÃO foram flexibilizados nesta correção. O teste agora comprova com `evaluate` real o snapshot ancestral que introduziu o manifesto exato, conserva todas as comparações de blobs sobre esse snapshot e testa HEAD separadamente. A recusa é obrigatória para HEAD classificado protegido; histórico inválido ou tentativa de aprovar migration no snapshot positivo falha.

`python -m unittest discover -s scripts -p test_release_candidate_policy.py`: **7testes aprovados,45,351s**, com Git e verificador reais, sem mocks/skip. Cobrem aprovação exata/documental, recusa de migration, blob adulterado, manifesto que tente admitir migration, pin falso e manifesto divergente. `python scripts/test_production_release_workflow_policy.py`: **publication_candidate_ready=false/api_fora_do_escopo; policy:ok**. Ruff dos dois arquivos aprovado. CI passa a executar também esses sete testes explicitamente; todos os checks anteriores permanecem. O head técnico final e o CI remoto ainda devem ser conferidos antes de declarar a integração aprovada.

A matriz77 anterior pode ser reutilizada para criptografia/gestão/migration não alteradas; a nova matriz37 repete todos os caminhos de checkout afetados pelo merge. Nenhum checkout real, segredo real, Oracle, migration remota, merge de PR ou deploy realizado. Fonte de release futura continua sendo o plano coordenado, não o botão do workflow0084.

## CI780 — falso positivo do gitleaks reproduzido e delimitado

Head2a3e7f7, CI780/run39696132166: etapa de varredura completa detectou somente uma ocorrência genérica na linha142 do recibo de homologação incorporado por cherry-pick b7f2090e. Inspeção autorizada do log exclusivamente em memória selecionou apenas metadados e mascarou o campo identificado. O conteúdo é o indicador público de comparação de distribuições com resultado passed, não chave ou segredo. Uma hipótese inicial de IDdecontainer foi descartada pela evidência; nenhuma exceção foi criada para essa hipótese.

Aplicada somente a fingerprint imutável do commit/arquivo/regra/linha em `.gitleaksignore`, seguindo o padrão existente. Nenhuma alteração de `.gitleaks.toml`, regra, caminho ignorado globalmente, workflow, scan de histórico ou histórico Git/forcepush.

Validação com **gitleaks8.24.3**, mesma versão do CI, pacote oficial Windows com SHA256 conferido; validaçãoHTTPS mantida. Ambiente Windows curl recusou download por verificação de revogação offline; download foi realizado pelo cliente HTTPS Python padrão, sem desabilitar certificado/hostname ou alterar configuração de máquina.

- Antes da exceção:1 ocorrência e exit1, fingerprintb7f2090e/validation.md/142, igual ao CI.
- Depois:0 ocorrências e exit0.
- Canário sintético independente em repositório temporário:1 ocorrência generic-api-key e exit1, comprovando que a regra continua ativa. Valor derivado de constante pública, sem uso em provedor, sem segredo real ou Git do produto.
- Clone temporário isolou as refs do candidato, preservando TODA sua ancestralidade e o scanner padrão. A primeira execução sobre o repositório local compartilhado encontrou a mesma ocorrência no recibo local não publicado2abb7d2 de uma branch irmã; essa ref não é ancestral do candidato nem estava no CI. Não foi criada exceção para ela. CI permanece varrendo seu histórico completo, sem redução de escopo.

Relatório local sanitizado: C:/codex-data/tmp/vault-gitleaks-fingerprint-validation.json; relatórios do scanner redigidos em100%. Resultado final de CI do novo head permanece pendente; backend e demais resultados do CI780 não são presumidos aprovados.

### Integração do ajuste de scanner de #266

Merge local afb6ee15 incorpora o ajuste de metadados de #266/320588ca. A fingerprint é idêntica à validada na task6.6; não há nova exceção. A admissão de `.gitleaksignore` é exata e não amplia runtime/migration. Nenhum arquivo de aplicação mudou após as matrizes37 PostgreSQL/610 frontend, cujas premissas permanecem válidas. A política técnica confirma novamente a recusa operacional deste candidato: publication_candidate_ready=false/api_fora_do_escopo; política0084 não autoriza publicação do cofre. O CI780 do head anterior falhou no scanner; não deve ser apresentado como aprovado. O novo head deve concluir todos os checks antes da integração.

Após esse merge:7 testes reais de política aprovados em32,097s; Ruff dos scripts aprovado; gitleaks8.24.3 novamente1 achado antes/0depois e canário1detectado; OpenSpec1.14.0 global134aprovados/0falhas. CI remoto do novo head permanece pendente.

## CI integrado confirmado antes da nova melhoria de apresentação

[CI782/39699171014](https://github.com/conradodeita/markina-gallery/actions/runs/39699171014), head27910b38adb90e31dd78db95698270de9f60d684:completed/success, todos os gates requeridos incluindo backend,frontend,scanner,OpenSpec,Gemma,imagens nativasAMD64/ARM64 e homolog-inventory-policy. PR262 confirmado open/draft com base main. Esse checkpoint conclui6.3; não aprova automaticamente o runtime posterior de hide-reopened-purchase-from-active-lists, cujo novo head terá CI próprio.
