# Integração final da correção Health opcional

## Resultado

Engenharia e publicação Oracle concluídas. A publicação posterior foi autorizada especificamente para `4b464f081dfa2451472848622853460398834e6d`; fechamento operacional no [registro da publicação](../remediate-frontend-dependency-vulnerabilities/production-publication-2026-10-19.md). PR [#228](https://github.com/conradodeita/markina-gallery/pull/228) integrado normalmente, sem bypass/force push, em 2026-10-19T01:43:48Z. Head ca606b0e654e8dae124c54cc37a3f03a21ec229a, árvore final a3920d01a2baa340ee953b893520a36d2bef1fb8 idêntica ao head. Commit de merge verificado pelo GitHub.

## Testes e revisão

A regressão com Docker CLI real/Bash e API sintética reproduziu exatamente a mensagem da Oracle antes da correção. Depois, passou com running/exited, Health/Status ausentes/null/vazios e healthy/unhealthy/starting, sem omitir migrate parado. Erro de inspect e falta de StartedAt obrigatório continuam bloqueando. Uma linha de template e três pins derivados foram alterados; nenhum gate de identidade/concorrência/escopo foi enfraquecido. Sem mudanças em produto, dependências, Docker/Compose ou workflows.

- Local: três testes reais do CLI, 32 contratos Linux, 11 testes de escopo e 12 de classificação aprovados; políticas, Ruff, Bash syntax, diff-check e OpenSpec estrito 122/122 aprovados.
- [CI do PR](https://github.com/conradodeita/markina-gallery/actions/runs/39183663312): success; 35 contratos (incluindo três regressões reais do CLI) passaram em 33,805 s. Backend: 1709 aprovados, 23 ignorados, 658 warnings, 1844,61 s.
- [CI pós-merge](https://github.com/conradodeita/markina-gallery/actions/runs/39186678648): completed/success; 35 contratos em 31,504 s; backend 1709 aprovados, 23 ignorados, 658 warnings, 1740,25 s. Nenhum check obrigatório pendente.
- Code Review inicial teve duas hipóteses contestadas com evidência em optional-health-validation.md. Revisão final local --base origin/main terminou com código 0 e sem defeitos acionáveis. Não é aprovação formal de terceiro no GitHub.

## Proteções e automações

Antes do merge: PR CLEAN/MERGEABLE, base main 34d2afd5, head esperado, seis checks obrigatórios success; main strict=true e enforce_admins=true, zero aprovações formais obrigatórias, sem exigência CODEOWNER/último push, linear=false e merge_commit permitido. Zero hooks/rulesets adicionais retornados. Sem alteração dessas proteções.

Workflows/classificador inalterados. Classificador antes do push e merge e no [job pós-merge](https://github.com/conradodeita/markina-gallery/actions/runs/39186678648/job/117858083859): baseline fe1f3bc6e1a483bd1ac5f4e71149f903e724873f, release_scope=none. Seis checks obrigatórios e classificador success; sete jobs skipped: deploy-homolog, production-preflight, production-release, production-app-preflight, production-app-release, production-app-rollback-preflight, production-app-rollback. Nenhum desses jobs executou. Apenas um run CI push para o SHA; deployments GitHub zero.

PR #177 permanece OPEN/base develop/head e9ce8405c1d53b8015e72b7f1f55a098329b3926. develop b4f15abd6a71585082758062feba7fcfcc225587, inalterados.

## Inventário histórico anterior à publicação — 2026-10-19T02:17:41Z

Revalidação às 2026-10-19T02:17:41Z: todos os 16 containers preservam identidade/estado/configuração/montagens (ordem normalizada); 15 ativos saudáveis e migrate histórico exited. Checkout e API APP_VERSION fe1f3bc6e1a483bd1ac5f4e71149f903e724873f; web sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573, mesma proveniência do release conjunto run 39135274157 tentativa 2/job 117710134038. Tags/marcadores/recibos/lock e hashes dos seis Compose/ambiente iguais ao inventário anterior; nenhuma escrita Oracle nesta engenharia. Estado/histórico graváveis, recursos disponíveis, lock livre, sem tentativa pendente, árvore limpa. Docker CLI Oracle 28.1.1; inventário independente por JSON, sem executar teste de produção ou novo helper.

HTTPS por leitura: saúde/API/raiz/pagamentos 200 e Estatísticas 404; sem OTP/transação real. Nenhum serviço reiniciado, imagem construída/retaggeada, banco/volume/foto alterado. Cache Git remoto ainda 34d2afd5, sem fetch do novo SHA. Naquele checkpoint a correção ainda não estava em produção; o estado final está no registro operacional.

O runbook e os helpers do SHA aprovado foram depois verificados e utilizados sob autorização operacional específica. A solicitação e os inventários preparatórios locais são evidências históricas; não representam pendências atuais. Auditoria do lockfile aprovado: zero vulnerabilidades runtime conhecidas e cinco altas em ferramentas dev, sem nova auditoria geral. Esta consolidação não sincroniza nem arquiva specs sem revisão humana.

## Publicação autorizada concluída em 19/10/2026

O proprietário autorizou especificamente o SHA 4b464f081dfa2451472848622853460398834e6d. Inventário real incluiu migrate sem Health sem falhar; adoção e preservação por ID concluídas. Release web-only saudável às 11:04:45 UTC, imagem sha256:6aef1935d8a4ba4bfc125a1bf5bea52ae6e26db361ef4942a1fedc55c4efc20a. Verificação independente final às 11:08:13 UTC: 15 serviços ativos saudáveis, todos os não-web intactos e sem tentativas pendentes. HTTPS/versões/asset público conferidos. Recuperação anterior 9567b1d8/fe1f3bc6 validada por rollback-inventory; não foi necessário executá-la. Detalhes e evidências em ../remediate-frontend-dependency-vulnerabilities/production-publication-2026-10-19.md. A autorização foi satisfeita somente para esta operação. Não sincronizar/arquivar sem revisão humana.
