# ATUALIZAÇÃO MAIS RECENTE — 11/11/2026

A recuperação assistida foi retomada e concluída10/10 localmente. Leia [handoff atualizado](../secure-photographer-account-recovery/pause-handoff.md) e validation.md da change. As referências6/10 e pausa abaixo são históricas. Nenhum push/produção/sync/archive.

---

# PAUSA MAIS RECENTE — 11/11/2026

Retomar pelo [handoff da recuperação de acesso](../secure-photographer-account-recovery/pause-handoff.md). Houve implementação local e validação posterior às seções históricas abaixo: change atual6/10; PostgreSQL25+37+3 aprovados, frontend focal30, jornada Chrome e seis combinações responsivas. Há pendências de fechamento, não há commit/push/produção. O proprietário pediu pausa por tokens; não prosseguir até nova ordem. validation.md da change atual distingue provas e limites. Esta seção substitui os trechos antigos que dizem não haver código/tasks0/10.

---

# Decisão substitutiva mais recente — recuperação manual, 10/11/2026

O proprietário autorizou a exceção manual: julga a identidade externamente e confirma recuperação no console. A prioridade continua nos meios anteriores verificados (e-mail/fatores; telefone somente com vínculo comprovado e mecanismo existente). Isso SUBSTITUI a decisão anterior de bloquear todos os casos sem fatores. Não coletar documento/selfie no SaaS, não exigir fator antigo na exceção; exigir proprietário reautenticado, declaração explícita, motivo, novo e-mail verificado e auditoria. Recuperação de credenciais não reabre conta encerrada nem retira suspensão.

Proposal/design/spec/tasks de `secure-photographer-account-recovery` e mapa central foram reconciliados e passaram strict. Nenhum código dessa change foi implementado; tasks continuam0/10. Primeiro inventariar consumidores e reconciliar segurança da identidade tardia antes de código. O proprietário não deve receber senha/códigos do tenant. Preservar todas as mudanças locais, sem push/produção por inferência. Esta seção prevalece sobre o bloqueio absoluto anterior descrito no histórico.

---

# Decisão mais recente — recuperação assistida, 10/11/2026

Proprietário escolheu implementar primeiro recuperação com meios anteriores válidos; quem perdeu e-mail, TOTP e todos os códigos fica bloqueado até futura política manual. Proposta `secure-photographer-account-recovery` foi reconciliada (proposal/design/spec/tasks), sem código; planejamento concluído, aguarda aplicação em pedido posterior. Tasks0/10. Atualizado mapa central `docs/saas-evolution/mapa-funcionamento-e-prazos.md`; noventa dias continuam não aprovados. Preservar alterações e provas anteriores; não há nova autorização de produção/push nem alteração de retenção.

---

# Atualização documental — 10/11/2026

Criada proposta `secure-photographer-account-recovery` (proposal/design/delta de auth), sem código, para identificação por nome/CPF, comprovação independente, troca assistida e reabertura separada. Não alterar automaticamente o fluxo de encerramento já validado. Falta decidir o procedimento quando também se perderam e-mail anterior e fatores; tasks dependem dessa resposta, não declarar implementação pronta.

Mapa central para futuro manual: `docs/saas-evolution/mapa-funcionamento-e-prazos.md`, com estados, prazos por evento, fontes, distinção local/produção e propostas pendentes. Noventa dias para contatos de clientes continuam não aprovados. Encerramento23/23, arquivo40/41 e exclusão auditada8/8 são estado local anterior preservado. Nenhum código, segredo ou produção alterado nesta atualização.

---

# ESTADO ATUAL — revisão concluída em 10/11/2026

Todas as sessões/laboratórios descritos abaixo terminaram; **não há execução própria pendente**. Última15393 terminou com falha de representação textual do índice, corrigida; repetição66410 (`pg-catalog-verified/`) passou **2/2 em37,06s**, cleanup0. Snapshot4b1aabcd0704867b7cd20a68f1119bf54846d51694173e1f6efc8af10800968d. Task3.3 do arquivo fechada com provas; arquivo frio40/41 (somente1.4 Workspace real pendente). Encerramento23/23, exclusão auditada8/8.

R5 geral:2.294 aprovados/142 skips, cobertura2.436 exata. Bateria PostgreSQL principal43 aprovados e dois contratos históricos corrigidos/repetidos2/2; facial/TOTP7/7. Quatro novos guards do reset passaram, inclusive registro surgindo entre conferências. Coleção Linux2.440 e Ruff passaram; políticas113+POSIX1 aprovados; owner-reset policy ok; Gitleaks último snapshot zero alertas com config existente; OpenSpec182/182 na versãoCI, change arquivo strict revalidada; diff --check passou. As correções posteriores de testes históricos tiveram prova focal, não repetir desnecessariamente toda a suíte sem mudança/risco novo. Não alegar CI remota ou SHA integrado.

**Pergunta enviada ao proprietário**: prazo de nome/telefone de cliente sem galeria acessível nem pedido/obrigação pendente; outras categorias separadas. Aguardando resposta, sem inventar duração. Próximo trabalho é reconciliar essa política no OpenSpec antes de comportamento novo, revisar restante da matriz/release. Nenhum commit/push/deploy, Oracle, Drive real, segredo operacional ou migration persistente realizado. Primeiro push continua condicionado à prontidão global; não sincronizar/arquivar sem revisão humana. Relatórios externos em `C:/codex-data/visualizations/2026/11/10/closure-review/`. Preservar worktree extensa e arquivo output vazio preexistente.

As seções abaixo são histórico e não prevalecem sobre este estado.

---

# CHECKPOINT MAIS RECENTE — 10/11/2026

Prosseguimento autorizado. Todas as execuções anteriormente listadas acabaram e seus containers foram removidos. R5:2.294 aprovados/142 skips, cobertura2.436 exata. Frontend687/build aprovado; OpenSpec182/182; Gitleaks final zero alertas; coleção Linux atual2.440 (quatro guards novos), Ruff passou. Políticas113+caso POSIX aprovado; owner-reset policy ok.

Correção do segundo consumidor de limpeza está implementada:23 tabelas SaaS preservadas, qualquer registro bloqueia reset, locks/rechecagem mantidos. Bateria Linux PostgreSQL `pg-linux-core/results.xml`:43 aprovados e dois casos históricos0070 falhos. Os módulos completos de reset (incluindo quatro guards novos) e compra de créditos passaram, inclusive concorrência/append-only. Os dois casos restantes eram comparação do catálogo0070 com ORM posterior. O helper agora usa colunas/tabelas anteriores + adições0070 e preserva a referência histórica dos predicados de índices. Ruff passou. Task3.3 do arquivo permanece reaberta até confirmar esta prova;1.4 Workspace real continua gate pós-release.

Sete testes PostgreSQL de facial/TOTP/recovery/migrations passaram em `pg-linux-special-final/results.xml`, laboratório próprio com hosts/portas exigidos. Corrigidas duas fixtures: tenant já semeado reutilizado; reconciliação criptográfica0092 usa adapter real e ORM legado, sem alegar que ORM atual funciona antes de0099. Nenhum guard foi relaxado.

**Única execução ativa: sessão15393**, runner externo `C:/codex-data/visualizations/2026/11/10/closure-review/run-pg-catalog-final.ps1`; reports `pg-catalog-final/execution.log` e `results.xml`. PG `pyp-saas-pg-linux-c6adfc27`, cliente `pyp-saas-pg-client-22fd3ae9`, labels saas-ci-pg/saas-ci-pg-client, namespace privado sem portas no host/tmpfs, finally verifica label e remove apenas o PG próprio. Snapshot `pg-catalog-final-source.tar.gz`, manifesto correspondente, hash0b97cd9b919c1a7c10f26fc467d02eef706af83d12e1c449662591788a2f2f56. Acompanhar antes de duplicar.

Próximo: confirmar dois testes históricos, corrigir divergência se houver; registrar evidência e fechar3.3 apenas validada. Atualizar checkpoint do candidato com resultados/limites. Nenhum commit/push/Oracle/Drive real/segredo ou operação persistente realizado. Preservar626 paths sujos e arquivo output vazio preexistente. Não sincronizar/arquivar specs sem revisão humana. Política de retenção de outras categorias e gates operacionais continuam sem decisão/ensaio; não inventar valores.

---

# ESTADO VIGENTE — continuação em execução, 10/11/2026

Pausa revogada. Nenhum commit/push/deploy, Oracle, Drive real, segredo operacional ou migration persistente nesta retomada. Preservar toda a worktree. Encerramento23/23 e exclusão auditada8/8 concluídos localmente. Arquivo frio39/41 temporariamente:1.4 ensaio real pós-release e3.3 reaberta pela integração de um segundo consumidor de limpeza, descrito abaixo.

## Provas concluídas

- Frontend687 aprovados, lint/typecheck/build já registrados. OpenSpec do CI1.14.0:182/182. Políticas de release113 aprovados/um skip Windows; o caso POSIX foi repetido no Linux e passou (um teste/três subtestes). Gitleaks8.24.3 do HEAD e625 paths pendentes passou com a configuração existente, sem nova exceção;42 alertas do snapshot completo são hashes históricos inalterados já tratados por fingerprints exatos.
- Linux r5 **2.294 aprovados,142 ignorados,zero falhas/erros**,2.436 itens cobertos uma única vez, três partes exit0 e mesma coleção. `backend_ci.py verify` passou. Fontes preservadas externamente em `r5-source.tar.gz`/`r5-source-manifest.json`, snapshot207451752e4fdd7e1328709bf25390c1359fac7955cb6e870f04ae3c7ea8137c. Containers r5 encerrados automaticamente; sessões37143/27019/70886 não são trabalho pendente.
- A última correção funcional da aplicação foi revalidação `platform_scope=True` no suporte TOTP; duas variantes HTTP passaram. Quatro fixtures históricas PostgreSQL posteriores foram corrigidas: seed obrigatório do proprietário e cadeia real0123 antes de usar o ORM atual. Maioridade/notificação/limpeza já passaram; prova financeira final segue no grupo abaixo.
- Qualidade/coleção Linux após quatro correções de fixtures: Ruff passou e os mesmos2.436 node IDs foram coletados, exit0. Snapshot7caf6335ce79c8848d3ac0f680ecee3bded4e24b307d610b7e8e99ad5b588105 em `candidate-final-source.tar.gz`. Não inclui a correção seguinte do reset.

## Integração atual — task3.3 do arquivo

A confirmação PostgreSQL encontrou o segundo consumidor `scripts/reset_homolog_owner.py` sem classificação de23 tabelas SaaS. A recusa era fail-closed correta; não se executou manutenção real. Task3.3 reaberta e design complementado **antes** do código. O script agora reutiliza as15 fontes centrais de histórico mais oito tabelas explícitas de perfil/aceite/segredo/configuração; todas são preservadas e qualquer registro bloqueia inventário elegível/reset antes de mídia/deletes. Mantém ambiente exclusivo de homologação, confirmação literal, proprietário e locks de todas as tabelas, com rechecagem pós-lock. Tabela desconhecida continua bloqueada. Nenhum recurso de produção é habilitado.

Foram adicionados quatro casos PostgreSQL em `test_tenant_owner_reset.py`: recusa com encerramento/perfil/coordenador e histórico inserido em outra conexão após a primeira conferência. Ruff focal e OpenSpec estrito passaram; **testes desses edits ainda em andamento**, não marcar3.3. `pg-remainder-final.xml` anterior parou em cinco falhas do classificador,9 aprovados/2 ignorados; não foi prova financeira final.

## Única execução ativa para acompanhar

- Sessão **38169**, runner externo `C:/codex-data/visualizations/2026/11/10/closure-review/run-pg-linux-confirmation.ps1`. Relatórios `pg-linux-confirmation/execution.log`, `results.xml`, `runtime.json`.
- PostgreSQL17.11 próprio `pyp-saas-pg-linux-757f7ecf`, label `pyp.synthetic-test=saas-ci-pg`, networknone/tmpfs512MiB, **sem porta no host**. Cliente `pyp-saas-pg-client-c87dcab7`, label `saas-ci-pg-client`, compartilha apenas esse namespace privado de loopback, read-only com tmpfs. Nenhuma rede externa ou volume de outro projeto. O finally verifica label e para somente esse PG; cliente --rm.
- RuntimeCI Python3.13.16/SQLAlchemy2.1.8; fonte `pg-linux-source.tar.gz`, manifesto `pg-linux-manifest.json`, snapshot **6bc4315c008151ef2885ca8ee9b9ef09007e9d5af4453c9ec05daf5315f1906f**. Seleção57 entradas em `pg-linux-targets.json`: inclui itens PostgreSQL não comprovados e módulos completos de reset/compra de créditos, com os quatro testes novos.
- Banco pyp_photographer_test no loopback privado15470; app_env_transition_test e totp_migration_test próprios; aliases de teste de transição/TOTP/facial/highres só neste processo. Demais laboratórios com portas/opt-ins específicos permanecem skip; discriminar resultados. Não imprimir senha/URLs.

Próximo: acompanhar execução, corrigir falhas reais, validar3.3 e reconciliar evidência/contagens. Depois revisar o candidato e os bloqueios de política/release, sem antecipar push. Uma falha não bloqueia os testes independentes. Não sincronizar/arquivar OpenSpec sem revisão humana. As seções seguintes são histórico e não prevalecem sobre este estado.

---

# CHECKPOINT VIGENTE — retomada em execução em 10/11/2026

O pedido de continuação revogou a pausa. Encerramento 23/23 e exclusão auditada 8/8 estão completos localmente; arquivo frio 40/41 conserva somente o ensaio Workspace pós-release/pré-tenants. Sem commit, push, Oracle, Drive real, segredos operacionais ou migrations persistentes. Preservar worktree integral.

## Resultado r3 e correção final

- Linux r3 concluiu 2.436 itens: 2.287 aprovados, 142 ignorados, sete falhas. Não é CI verde. Acervo: fixtures sem prazo finito corrigidas para 14 dias explícitos, 19 aprovados em 282,77 s. Console: whitelist mantém privacidade, sem confundir frase de confirmação com campo CPF.
- Confirmação focal posterior: 13 aprovados/duas falhas identificaram uma revalidação operacional restante no suporte TOTP. `photographer_totp_support.revoke` agora usa o escopo global explícito do proprietário também antes do commit, como `console.authorized`. Duas variantes HTTP passaram em 34,23 s (sessão normal e alterada). Não remove reautenticação, comparação de sessão ou check do proprietário. Ruff focal aprovado.
- r4 interrompida somente nos containers próprios por seu snapshot anteceder a correção final. Logs parciais preservados; não contar como cobertura completa.

## Execuções ativas para acompanhar

- **Linux r5**, snapshot imutável `207451752e4fdd7e1328709bf25390c1359fac7955cb6e870f04ae3c7ea8137c`, 2.616 arquivos; imagem de ensaio já registrada abaixo, Python 3.13.16. Fontes excluem .env/segredos/bancos/caches/runtime. Sem rede, portas ou volumes de terceiros.
- Relatórios `C:/codex-data/visualizations/2026/11/10/closure-review/linux-ci-r5/shard-{0,1,2}/`. Scripts `run-linux-r5-shard-{n}.ps1` no diretório externo. Parte 0 sessão **37143**, container `pyp-saas-ci-0-57750cd5`; parte 1 **27019**, `pyp-saas-ci-1-89fcba57`; parte 2 **70886**, `pyp-saas-ci-2-e4027f6f`. Label `pyp.synthetic-test=saas-ci`, --rm, quotas próprias. Acompanhar até terminar; verificar cobertura pelo helper somente se três exits zero e mesma coleção/snapshot.
- **PostgreSQL separado**, sessão **42726**, container próprio `pyp-media-deletion-test-6e8f706855`, label `pyp.synthetic-test=audited-media-deletion`. PostgreSQL 17.11 local tmpfs, loopback15470/pyp_photographer_test, credencial sintética de processo, limpeza automática finally com label verificada. Runner externo `run-pg-skips.ps1`; seleciona os node IDs ignorados em r3, exceto UI/Compose/backup opt-in, e duas variantes TOTP corrigidas. Variáveis opcionais de outros laboratórios não configuradas continuam skips; registrar contagens, não alegar ausência total de skips. XML `pg-skips-confirmation.xml`.
- Gitleaks 8.24.3: histórico alcançável por HEAD passou com redação integral e config existente. Snapshot r5 tem42 alertas em três arquivos históricos não modificados; conferidos contra fingerprints exatos já presentes no ignore, hashes/fingerprints públicos. Nenhuma allowlist nova. Varredura restrita aos paths pendentes segue separada; relatórios externos redigidos. Não confundir consulta a todas as refs locais (um alerta em branch antiga não ancestral) com HEAD.
- Matriz de retenção reconciliada com as decisões de encerramento e arquivo já aprovadas; prazos das outras categorias não foram inventados. Deltas billing corrigiram referência obsoleta a MFA obrigatório, conforme onboarding progressivo aprovado. Só documentação após o snapshot final; nenhuma mudança funcional posterior à correção de TOTP.

Continuar acompanhando provas, corrigir falhas com validação focada, registrar agregado e limites. Primeiro push permanece bloqueado pela prontidão global e revisão; nenhuma sincronização/arquivo OpenSpec por inferência.

---

# RETOMADA VIGENTE — autorizada pelo proprietário em 10/11/2026

A pausa abaixo foi revogada pelo pedido explícito de continuar exatamente deste ponto. Conferido Docker `desktop-linux`, imagem sintética preservada e nenhuma execução anterior ativa. Três falhas registradas no log incompleto de r2 foram identificadas pelos node IDs e reproduzidas nativamente: duas expectativas antigas de busca de carteiras (nome/identidade ambígua) e uma expectativa de aceitar campo extra em edição que agora o contrato recusa. Foram corrigidos somente os testes conforme specs aprovadas: **12 aprovados**, seis avisos conhecidos, 157,14 s e Ruff aprovado. Nenhuma mudança produtiva, push ou migração persistente autorizada por essa retomada.

## Execução ativa r3

- Snapshot imutável atualizado `39dab99f06bdc67e6e1685db604a6f514047b38e7cdb21137791be15afde54bc`, 2.616 arquivos. `candidate-source.tar.gz` e manifesto no diretório externo já citado; sem `.env`, credenciais, bancos, caches ou runtime.
- Relatórios novos em `C:/codex-data/visualizations/2026/11/10/closure-review/linux-ci-r3/shard-{0,1,2}/`. Mantidos r1/r2 sem sobrescrita. Logs agora identificam cada node ID (`PYTEST_ADDOPTS` com `-vv`), além dos JSON/XML finais.
- Parte 0: sessão **8945**, container `pyp-saas-ci-0-40b1d857`; parte 1: **53529**, `pyp-saas-ci-1-de358090`; parte 2: **97332**, `pyp-saas-ci-2-609615c6`. Label própria `pyp.synthetic-test=saas-ci`, `--rm`, sem rede/portas, 2 CPU, memória 2 GiB, tmpfs temporário de 1,5 GiB por parte. Scripts reproduzíveis fora do Git `run-linux-r3-shard-{n}.ps1`; recusam sobrescrever log existente.
- Repetição em andamento: acompanhar as três sessões, sem duplicar ou alterar recursos preexistentes; corrigir falhas com prova focal e não considerar tentativa incompleta como cobertura completa. Conferir `scripts/backend_ci.py verify` apenas com três exits zero/mesmo snapshot/mesma coleção. Testes PostgreSQL indisponíveis neste runtime isolado devem ser discriminados dos contratos PostgreSQL já aprovados e de novas provas eventualmente necessárias.
- Ruff geral também passou no runtime Linux/Python 3.13.16 com a versão de dependências efetivamente resolvida do CI; container efêmero de qualidade encerrado automaticamente. Não houve mudança funcional no backend durante esta retomada.

---

# Histórico da pausa — solicitada pelo proprietário em 10/11/2026

**Não retomar desenvolvimento/testes até novo pedido do proprietário.** A pausa foi pedida durante a repetição Linux geral. As três execuções próprias receberam SIGINT; duas concluíram a interrupção e a terceira precisou de parada delimitada do container próprio. Fontes, alterações e relatórios parciais foram preservados. Nada foi commitado, enviado ou operado em produção.

## Ponto exato para a próxima retomada

1. Ler este checkpoint, os artefatos e `docs/saas-evolution/candidate-validation-2026-11-03.md`. Encerramento local está **23/23**; arquivo frio **40/41**, faltando somente ensaio real Workspace pós-release/pré-tenants. Não sincronizar/arquivar sem revisão humana, não realizar primeiro push por inferência.
2. Frontend geral **687 aprovados**; build final aprovado; lint zero erros/38 warnings; 13 testes de layout repetidos após fortalecer a detecção de comentários/seletores passaram. O teste agora exige encontrar a regra, evitando uma checagem vazia. Nenhuma alteração funcional frontend depois do build além dessa correção de teste.
3. Backend Windows amplo teve 1.250 aprovados/30 skips/10 falhas antes do maxfail; os grupos detectados foram corrigidos e suas provas focais passaram. A validação geral Linux ainda **não terminou**, portanto não declarar CI completa ou prontidão de push. OpenSpec global na versão exata do CI 1.14.0 passou **182/182**; a versão global 1.14.1 tem 29 avisos longos tratados como falha e não é a versão do workflow.
4. Relatórios da repetição pausada: `C:/codex-data/visualizations/2026/11/10/closure-review/linux-ci-r2/shard-{0,1,2}/`. Parte 0: 114 aprovados/um skip antes da interrupção; parte 2: 344 aprovados/dois skips. A parte 1 estava acima de 79% e não recebeu conclusão válida antes da parada; conferir o log, sem somar resultados parciais como cobertura completa. Toda a evidência é sintética.
5. Para continuar a validação, conferir primeiro Docker `desktop-linux` disponível e ausência das execuções próprias anteriores. Imagem de teste amd64 já preparada `pyp-saas-ci-local:20261110`, digest registrado abaixo. Snapshot backend usado é imutável `f87084374211e37e217156c49ef2b40c63068f57bd44617eff3de1d374e6e4e5`; fontes/manifesto e três scripts `resume-linux-shard-{0,1,2}.ps1` estão no mesmo diretório externo. Esses scripts reproduzem a configuração r2 (sem rede, com tmpfs), mas **escolher novo diretório de relatórios antes de executá-los para preservar os resultados da pausa**. Se modificar fontes, gerar outro snapshot e atualizar a identificação; não confundir snapshot com SHA Git. A última correção somente do teste frontend de layout é posterior ao snapshot Linux e teve prova própria.
6. Reexecutar as partes interrompidas somente quando a pausa for revogada, acompanhar todas, investigar falhas e verificar cobertura com `scripts/backend_ci.py verify` só com três exits zero/mesma coleção. Os testes PostgreSQL não estão disponíveis dentro desse runtime Linux; distinguir seus skips das provas nativas PostgreSQL já registradas. Não executar Drive, servidor, push ou migrations persistentes para satisfazer esse gate local.

As seções seguintes são histórico de progresso e comandos/contexto; esta seção prevalece sobre instruções antigas de execução em andamento.

---

# Continuidade anterior — 10/11/2026 (superada pela pausa acima)

A pausa anterior foi revogada pelos pedidos posteriores de continuar. A change `add-photographer-account-closure` está **23/23 concluída e validada localmente**; `tasks.md`, `design.md`, delta specs e os checkpoints finais de `validation.md` são a fonte atual. A implementação parcial descrita abaixo foi terminada. Não sincronizar/arquivar sem revisão humana; não fazer push ou operar produção por inferência.

## Última decisão e implementação

- Após dez anos, o proprietário pode remover explicitamente CPF/endereço cifrados do perfil, com revisão, senha/TOTP, frase e auditoria. Nome/e-mail mínimos, financeiro/aceites e HMAC versionado permanecem pelas regras próprias. O HMAC só sai após exclusão integral e auditada da mídia (`add-audited-tenant-media-deletion`, 8/8).
- Novo serviço `tenant_profile_retention.py`, endpoint `/admin/platform/console/tenants/{tenant_id}/closure/profile-reduction`, migration aditiva 0123, UI do console. A ação não arquiva/exclui mídia, reabre conta nem altera créditos. Chave ausente, comparação divergente, obrigação pendente ou recibo de exclusão adulterado bloqueia.
- Depois de reabrir perfil reduzido, compra/checkout exigem CPF correspondente ao HMAC mantido e endereço novamente. Nome completo não é pedido outra vez. Revisão dos Termos padrão local acompanha a regra; nenhum texto produtivo publicado.
- PostgreSQL descartável: 14 testes novos + migration 0123 + dez do avaliador aprovados; repetição integrada de identidade/signup/recovery/media-deletion **66 aprovados, zero skips**. São 91 contratos distintos. Nos testes, corrigidos locks de chamadas diretas com commit/rollback antes de outra conexão HTTP; não relaxados guards/locks do runtime.
- UI autenticada real no Chrome: encerramento pendente, contador fechado, vazio/carregamento/falha, revisão CPF/endereço recusada e bem-sucedida, auditoria e ausência do botão após sucesso. 390/768/1440 e oito temas. 23 testes focados frontend, ESLint, TypeScript, build, Ruff e OpenSpec strict aprovados. Capturas apenas sintéticas fora do Git em `C:/codex-data/visualizations/2026/11/10/closure-review/`.
- Runner visual guardado `scripts/local_tenant_closure_demo.py`: somente DB vazio loopback 15478 `pyp_closure_ui`, API 8000, origem 3039, revisão exata 0123; login normal sem bypass e chaves sintéticas de processo. API/frontend/container próprios já encerrados; não reutilizar ou remover recursos preexistentes.

## Ponto seguinte do candidato

A revisão geral pré-push está em execução. Primeira suíte frontend: 683 aprovados/3 falhas em 87 arquivos; duas falhas temporais passaram em repetição com dois workers (87 testes). A outra detectou cap global de 1440 px contrário ao layout fluido: removidos somente cap/centralização adicionados pelo arquivo frio, corrigida a seleção exata no leitor de CSS do teste e adicionada regressão (13 aprovados). Repetição frontend integral com dois workers e suíte backend geral estão em andamento; não presumir seus resultados. Relatórios externos ao Git no mesmo diretório de capturas (`frontend-integration.json/log`, `backend-integration.xml`). Resultados finais devem ser registrados no checklist do candidato.

Preservar toda a worktree. O HEAD continua `855be42b826c61c8ebdb2bd1e471ca1d28147061`, branch `feature/saas-release-candidate`; ainda não há SHA integrado/commit/push. O primeiro push depende de 100% do escopo local e da revisão do candidato. Arquivo/backup Workspace reais, certificado/rota wildcard e ensaio remoto continuam gates próprios de produção pré-tenants; fidelidade foi adiada. A matriz global de retenção ainda tem categorias não decididas e não deve ser preenchida por inferência.

---

# Histórico da pausa — 09/11/2026 (superado; não usar como estado atual)

## Ordem vigente

O proprietário pediu pausa por limite de tokens. Não continuar implementação até novo pedido. Worktree `C:/codex-data/worktrees/saas-release-candidate/Photo Delivery` está extensamente suja; preservar integralmente. Primeiro push somente a 100% do escopo local combinado. Nenhum commit, push, deploy ou alteração produtiva foi realizado nesta sessão.

## Change atual

`add-photographer-account-closure`, workflow apply explicitamente autorizado. Ler mandato, roadmap, config, política de refatoração, proposal/design/specs/tasks e `validation.md`. Tasks 1.1–3.3 estão marcadas, total 9/23; seção 4 está parcialmente implementada e **não validada**, não marcar concluída nem abrir outra frente antes de concluí-la ou registrar bloqueio real. Provas da seção 3 são do checkpoint anterior às alterações parciais da seção 4.

## Decisões adicionais aprovadas durante aplicação

1. Pastas comprovadamente nunca liberadas podem arquivar diretamente no encerramento, sem aguardar 30 dias, depois de conferir pedidos/obrigações/jobs/reservas e integridade. Histórico incerto conserva o bloqueio. Já liberadas seguem seus prazos.
2. Capa sem nenhuma pasta de fotos pode arquivar como unidade técnica e recuperar junto da conta **sem taxa adicional**. Não apresentar/cobrar unidade técnica como pasta de fotos. Com conteúdo, capa continua com a última pasta ativa.
3. CPF confirma o cadastro na recuperação depois de dez anos, por impressão protegida mantida enquanto houver mídia recuperável; apagar esse verificador com a exclusão explícita da mídia. Não é autenticação independente: proprietário continua decidindo reabertura por ação sensível autenticada/auditada; dados atuais e e-mail verificado necessários. Nome/e-mail operacionais têm janela de dez anos; mídia sem expurgo automático, contador e revisão manual no console.

As decisões estão em proposal/design/spec de lifecycle. Não sincronizar specs principais nem arquivar sem revisão humana.

## Implementado e validado até a seção 3

- `Tenant.lifecycle` open/closing/closed separado de suspensão; `TenantClosureRequest`, migration aditiva 0117.
- `tenant_closure.py`: solicitação com papel/vínculo/e-mail verificado, saldo/Termos esperados, idempotência e lock; `require_new_work`; finalização atômica com avaliação, revogação de sessões/push, auditoria e preservação do saldo.
- Bloqueios pré-body/reserva nas rotas de galerias/pastas/fotos/capas/JPEG, readiness legado e reserva de créditos.
- Guards de sessão/tenant/host, filas e escopo global explícito do proprietário; exceções internas de conciliação e retenção não autorizam login ou novo checkout.
- Lock de tenant e revalidação pós-lock nos caminhos de checkout gratuito/manual e compras de créditos para serializar com encerramento.
- `tenant_closure_obligations.py`: avaliação tenant-scoped conservadora, prazos/reaberturas, pedidos, pagamentos, revisão financeira, jobs/reservas e catálogo/manifesto; fonte indisponível não libera fechamento.
- Scheduler/guard/manifesto existentes suportam draft nunca liberado e capa isolada, sem outra fila/adapter. `order_delivery.unresolved_order_condition` compartilha critério de obrigação.
- Worker `process_next_tenant_closure`, cursor em memória para não deixar conta bloqueada impedir avaliação das demais; chamado no ciclo geral antes da cadeia OR de jobs.
- Ainda **não existe rota HTTP de solicitação nem UI do encerramento**: exposição depende de integração completa. Não anunciar fluxo concluído.

## Evidências do checkpoint (não são validação do código parcial da seção 4)

- 50 testes de autenticação/console/notificações/dispatcher aprovados (593,67 s); ajustes posteriores cobertos em testes focados. Avisos conhecidos de lifespan e ciclos de FKs SQLite.
- Webhook Orders em open/closing/closed: 3 aprovados (37,24 s).
- Migration 0117/corrida PostgreSQL/avaliador: 11 aprovados (22,83 s), incluindo checkout versus finalização, histórico preservado e recusa de downgrade com dados.
- Avaliador/finalização: 10 aprovados (6,93 s), incluindo saldo positivo confirmado preservado, sessão revogada por releitura e rotação do worker.
- Dispatcher: três arquivamentos completos (expirada, draft, capa isolada) aprovados (3,58 s); readback corrompido conserva mídia/closing: 1 aprovado (3,26 s).
- Avaliador/dispatcher/executor anterior: 23 aprovados; scheduler intermediário teve 3 PostgreSQL ignorados, devem ser reexecutados no checkpoint integrado.
- Ruff passou no checkpoint até seção 3. Não presumir que ainda passa depois dos edits da seção 4.

## Seção 4 — código parcial, próximo ponto exato

Arquivos adicionados/alterados **ainda sem validação**:

- `auth.py`: modelos `TenantClosureRecoveryBatch`/`TenantClosureRecoveryItem`; `MediaArchiveRecoveryRequest` ganhou `closure_batch_id`, `technical_cover_exempt`, novas FKs/checks. Separar isenção da capa de `owner_exempt` para não inventar que todo tenant é proprietário.
- Migration `20261109_0118_closure_recovery_batch.py`: cria lote/itens e altera shape de autor/isencão. Nunca executada; revisar e testar em PostgreSQL descartável com preservação de dados e recusa de downgrade com histórico.
- `tenant_closure_recovery.py`: orquestração de lote, payload sanitizado, escopo interno de manutenção de conta fechada e prova de lease ligada a lote/item/PlatformOwner. Request batch reaproveita `media_archive_billing.request_recovery`; precisa de testes reais com adapter sintético.
- `media_archive_billing.py`: argumento interno `closure_batch_id`; autor owner em primeira recuperação administrativa; derivação da isenção técnica e atualização do item no retry. **Último Ruff acusou SIM102** em `if requester_type == 'owner': if not actor_is_owner` (por volta de linha 331). Imports foram organizados automaticamente. Nenhum teste rodou após essas alterações.
- `media_archive_worker.py`: importa `recovery_is_exempt`, usa isenção geral em validação de reserva, permite buscar cover_assets no restore, aceita manifesto com zero objetos (`<0`, antes `<=0`) e não inicia prazo de acesso na capa. `_locked_claim` liga escopo de recuperação ao lote com lease verificado.
- `acervo_context.py` e `tenancy.py`: escopo `tenant_archive_recovery` por transação; capacidade `closure_archive_execution` persiste na sessão do worker entre commits, mas deve ser revalidada no banco por operação/tenant/lease/autor a cada acesso. Conferir que nenhuma sessão normal, lease expirado ou outro tenant usa esse caminho. É a área mais sensível da implementação parcial.

### Continuar nesta ordem

1. Rever a seção 4 parcial antes de novos edits; corrigir SIM102 e executar import/compile para detectar ciclos entre billing/worker/recovery.
2. Completar validações de `technical_cover_exempt` no worker/payload; conferir idempotência de retry com lote herdado (derivação antecipada foi adicionada em billing, ainda não testada).
3. Criar fixture sintética de conta encerrada com mídia realmente arquivada para testar lote. `_archive_fixture` em `test_media_archive_executor.py` não cria administradores/carteira; adicionar identidades sintéticas para esse tenant, PlatformOwner em tenant separado, carteira finita, saldo e preço. `_restore_fixture` já cria pedido/claim de restore, portanto não reutilizar como se estivesse livre de operações.
4. Testar lote owner-only, isolamento/FKs, idempotência, falha parcial/retry, prioridade global, saldo/capacidade, débito só no sucesso e capa sem taxa. Sem qualquer Drive real.
5. Implementar reabertura separada e completa (4.3), preparando gate de CPF depois de dez anos sem autoativação. Depois seção 5, UI/Termos e testes integrados, conforme tasks.
6. Reexecutar checks afetados, registrar evidências e marcar cada task só após conclusão. Continuar enquanto houver trabalho local seguro; não publicar nem operar produção por inferência.

## Laboratório local deixado ativo

Docker context verificado `desktop-linux`; criado somente `pyp-closure-db-20261109`, label `pyp.task=tenant-closure`, PostgreSQL 17.11, tmpfs sem volume persistente, loopback **15476**, banco **pyp_photographer_test**. Credencial exclusivamente sintética usada nos comandos da sessão (não é segredo operacional). Não parar/remover o laboratório preexistente `pyp-archive-ui-20261109` em 15473. Nenhum `.env` real foi editado.

Para testes PostgreSQL, definir apenas no processo a URL sintética local e `PHOTOGRAPHER_TEST_DATABASE_PORT=15476`; fixture `postgres_schema` limita host/banco/porta e cria schemas aleatórios. Executável `backend/.venv/Scripts/python.exe`. Não usar banco persistente. Após concluir os ensaios, remover apenas o container criado para esta task, com identificação conferida.

## Panorama comunicado ao proprietário

Consulta mecânica de 17 frentes principais no OpenSpec: 210/252 tarefas marcadas (83,3%) quando a change tinha 3/23; depois avançou até 9/23. Isso não é percentual confiável do esforço restante nem prontidão produtiva e o filtro não é exaustivo. Candidato integrado, revisão de diff e CI local no SHA exato permanecem pré-push. Drive/Workspace reais são pós-release/pré-tenants, exclusivamente com ensaio do proprietário e autorização própria. Fidelidade adiada. Não alegar 100% nem fazer primeiro push.

## Checkpoint que substitui o ponto seguinte acima — regressão geral 10/11

- Encerramento continua 23/23; arquivo frio agora 40/41 (nova task 3.3 de integração validada; única aberta é ensaio real 1.4). Classificadas 19 tabelas novas como preservadas no inventário e acrescentado bloqueio da limpeza legada sob lock quando há histórico nas 15 fontes de arquivo/encerramento. Provas: 17 testes + um skip de limpeza destrutiva legada, mais um teste PostgreSQL real de recusa/preservação e inserção concorrente bloqueada. Nenhuma limpeza persistente executada.
- Frontend geral **687/687**, lint zero erros/38 warnings e build final aprovado. Backend Windows amplo terminou com 1.250 pass/30 skip/10 falhas em 5.652,56 s (parada maxfail); os dez casos foram corrigidos/reconciliados em testes focados. Novos contratos `media_state`, mocks de filas e conciliação prévia de suspenso eram expectativas antigas; não regredir as regras aprovadas para satisfazê-las.
- Global OpenSpec **182/182 verde na versão exata do CI, 1.14.0**, executada via npx offline. Global instalado 1.14.1 recusa 29 artefatos por warnings novos de parágrafos longos; não são falhas na versão do CI. Não foi reescrita nenhuma spec publicada por isso. Relatórios externos ao Git `openspec-ci-version.json` e `openspec-all.json`.
- `git ls-remote` somente leitura confirmou main remoto ainda no mesmo HEAD `855be42b826c61c8ebdb2bd1e471ca1d28147061`. Sem commit/push.
- Docker Desktop esteve desligado; o proprietário abriu e o motor voltou. Não iniciar/reiniciar daemon por inferência. Criada só a imagem local de teste amd64 `pyp-saas-ci-local:20261110` (`sha256:3cdb8fecb477768ffce65abc6ec51ea584cd1920350fc55fb41f4b2cc4603116`), Python 3.13.16 e requirements atuais do CI. Não é imagem de release. Nenhum modelo/peso/engine real ativado.
- Linux primeira tentativa em `C:/codex-data/visualizations/2026/11/10/closure-review/linux-ci/`: tmpfs 512 MiB insuficiente para centenas de SQLite. Uma parte terminou com 629 pass/28 skip, uma falha de introspecção interna do FastAPI e nove erros de quota. As outras duas partes foram interrompidas com SIGINT após conferir label própria; não são cobertura completa. O teste de identidade agora exerce a rota main por HTTP em vez de inspecionar routers lazy, e passou nativamente.
- **Ponto ativo exato:** repetição Linux em três containers novos sem rede/portas, fonte em tmpfs, 2 CPU, memória 2 GiB, tmpfs `/tmp` 1,5 GiB cada. Snapshot imutável de fontes `f87084374211e37e217156c49ef2b40c63068f57bd44617eff3de1d374e6e4e5`, 2.616 arquivos, sem `.env`, credenciais, bancos/cache/runtime/output. Usa `scripts/backend_ci.py`, 2.436 itens, três partes de 812, maxfail=10. Relatórios em `.../closure-review/linux-ci-r2/shard-{0,1,2}/execution.log`, `shard-{n}.json/xml`, `runtime.json`. Ainda não assumir sucesso. A configuração/execução não disponibiliza PostgreSQL para os testes nessa imagem; skips devem ser separados das provas PostgreSQL nativas já executadas.
- Sessões em andamento (somente desta retomada): parte 0 **32670**, container `pyp-saas-ci-0-98e0cf53`; parte 1 **33627**, `pyp-saas-ci-1-0f734a26`; parte 2 **77733**, `pyp-saas-ci-2-c6abdeed`. Todos label `pyp.synthetic-test=saas-ci`, `--rm`; acompanhar, investigar qualquer falha, não duplicar execuções nem parar recursos alheios. A imagem/cópias só são de teste; não existe deploy.
- Ao concluir as três partes, ler JSON/XML e validar cobertura pelo `scripts/backend_ci.py verify` apenas se todas tiverem exit zero e coleção/id de snapshot idênticos; corrigir regressões, não somar tentativas parciais para declarar verde. Registrar resultados e atualizar este checkpoint. `docs/saas-evolution/candidate-validation-2026-11-03.md` contém a evidência e os gates gerais. O ensaio Workspace e demais operações remotas seguem separados e não autorizados por esse teste local.
