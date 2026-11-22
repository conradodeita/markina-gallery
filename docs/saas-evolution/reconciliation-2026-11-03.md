# Reconciliação de continuidade — 03/11/2026

## Evidência local atual

- Diretório confirmado: `C:/codex-data/worktrees/pickyourpic-saas-main/Photo Delivery`.
- Branch `feature/pickyourpic-saas-mainline`, HEAD `6af538ecd5c46da7691fa973c33869f263945a25`.
- `git rev-parse origin/main` e `git ls-remote origin refs/heads/main` retornaram `855be42b826c61c8ebdb2bd1e471ca1d28147061`.
- Inventário inicial: 73 arquivos tracked com diff (3.737 inserções/321 exclusões), além de numerosos arquivos untracked de TOTP, carteira, compras e planejamento. Todos preservados. Contagem não inclui as edições desta retomada.
- `git diff --name-only 6af538ec origin/main` identifica evolução facial/operação/CI/AGENTS. Não há patch upstream de console, carteira ou portal nesse intervalo. Existem sobreposições em módulos/testes faciais, scripts e a change de restauração já copiada localmente; não substituir esses paths indiscriminadamente.

## Separação do runtime

O snapshot de 01–02/11 (API `74f613`, worker `c1944189`) é histórico. O repasse operacional registra overlays faciais mínimos e correção de ambiente de notificação, sem deploy integral do main ou do SaaS. Referência atual dessa frente: worktree `facial-restore-support`, commit `144eb5c8`, draft PR #364. Main foi confirmado aqui; configuração/serviços remotos não foram reinspecionados nesta sessão.

Pendências de notificação/SLO da frente facial não bloqueiam implementação local do console/portal. Não reiniciar calibração, reindexar ou repor gates operacionais antigos a partir desta cópia. Nenhuma autorização facial é liberação para publicar SaaS ou executar 0091–0096 remotamente.

## Plano seguro de integração

Condição posterior do proprietário: a produção atende clientes e permanece ativa. Esta preparação é local; nenhum release pode desligar serviços ou suspender tenants. Se uma etapa futura exigir indisponibilidade temporária, o executor deve apresentar alcance, duração estimada, janela e retorno e obter consentimento específico antes de executá-la. O contract TOTP `0093` e a troca de API/worker exigem ensaio de continuidade; não presumir impacto zero.

1. Preservar diff completo (tracked/untracked) e autoria/escopo antes de formar commits pequenos. Não adicionar artefatos de teste, .env ou secrets. Revisar os arquivos atualmente untracked como parte do código, não como descartáveis.
2. Comparar semanticamente cada path sobreposto com `origin/main`, usando cópias temporárias externas e merge de três vias somente nessas cópias para produzir uma proposta revisável. Não executar pull/rebase/cherry-pick amplo sobre esta árvore suja.
3. Reconciliar AGENTS/CI e patches faciais atuais separadamente do código comercial. A fonte de status operacional é a frente própria; nenhuma cópia local antiga prova runtime atual.
4. Após revisão do diff/commits e ponto de preservação adequado, integrar a base main e repetir validações afetadas (especialmente auth, workers, pagamentos e facial), sem perder o SaaS local.
5. Antes de release futuro, inventariar runtimes reais, schema/consumidores, configuração, backups/restore e plano de impacto zero. Validar a candidata completa e obter autorização operacional específica. Main verde não prova produção nem compatibilidade de todos os módulos.

Não foi feita integração Git, commit, push, release ou alteração remota nesta retomada. A base antiga é uma limitação explícita do resultado local, não uma suposição de paridade com produção.

## Comparação local posterior com o `main` atual

`origin/main` foi reconfirmado em `855be42b` por `git ls-remote`. No inventário inicial havia 27 paths sobrepostos entre a evolução do `main` e o trabalho local: 7 tinham blob idêntico, 20 diferiam. Dois módulos de runtime facial foram reconciliados localmente depois da comparação semântica; agora seus blobs correspondem exatamente ao `main`. Nenhum merge/rebase amplo foi feito.

| Path | Alteração local | Alteração em `main` | Direção para o candidato |
| --- | --- | --- | --- |
| `backend/app/facial/config.py` | Acrescentava `require_explicit_rollout` e lia `FACIAL_REQUIRE_EXPLICIT_ROLLOUT`. | Contém as mesmas adições e também `require_production_calibration` com padrão verdadeiro. | Adições do `main` aplicadas; hash do blob local agora igual ao do `main`. |
| `backend/app/facial/rollout.py` | Exigia rollout explícito quando configurado. | Contém a mesma condição e a proteção adicional `calibration_allows_processing`, inclusive verificação de owner ativo. | Adições do `main` aplicadas; hash do blob local agora igual ao do `main`. |
| `backend/app/facial/face_worker.py` | Blob local e blob de `main` são idênticos. | Sem diferença de conteúdo. | Pode ser tratado como reconciliado por conteúdo, mas ainda depende do teste da imagem final. |

Os dois arquivos de teste diretamente afetados foram acrescidos dos casos do `main` para calibração explícita, owner ativo e rollout; seus casos locais anteriores foram preservados. `test_facial_config.py` e `test_facial_rollout.py`: **54 passed** após a reconciliação. A nova contagem por hash mostra 17 paths com blobs divergentes, incluindo esses testes (que contêm casos locais adicionais), scripts de restauração e artefatos OpenSpec. Não aplicar merge amplo antes de revisão semântica de cada um. Esta validação local não comprova prontidão de deploy nem autoriza qualquer interrupção de produção.

Revisão delimitada dos scripts de restauração: o `main` acrescentou fases e verificações operacionais posteriores à cópia local, inclusive no CLI e no host. Os scripts locais também têm linhas próprias (por exemplo, paths e gate de calibração antigos), então uma cópia por arquivo ou um merge textual automático não prova equivalência operacional. Para o candidato SaaS, manter a implementação de restauração do `main` como base e portar apenas diferenças SaaS demonstradas necessárias; não usar os scripts locais antigos para operar produção. Nenhum script foi executado contra o servidor ou alterado nesta revisão.
