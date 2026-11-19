# Evidências e continuidade

## Autorizações e alvo

- 18/11/2026: proprietário escolheu ponte root-only restrita e autorizou explicitamente prova semântica por serviço para API/web sem `config-hash`.
- Autorização da conversa cobre commit/push, correções de CI, PR/merge e deploy protegido. Preservar gates, dados reais e flag facial `true`; não alterar secrets, `.env`, banco, migrations, workers ou serviços vizinhos.
- Worktree: `C:\codex-data\worktrees\saas-release-candidate\Photo Delivery`; branch de follow-up `fix/accept-github-scp-app-bridge-origin`. O caminho preexistente `output` está fora do escopo.

## Diagnóstico read-only do host

SSH sem sudo confirmou host `clearbudget-vnic`, checkout `bfe511f850224823254b0fc9f51fa7ff60ecfba0`, API/web saudáveis e imagens por IDs imutáveis. Cada serviço usa snapshots diferentes, web tem diretório histórico em `deploy-state`, ambos sem label `config-hash`. O recibo `web-current.identity` é anterior à imagem ativa. Nenhuma fonte protegida foi aberta e nenhuma alteração remota foi executada durante este diagnóstico.

## Gates locais

| Gate | Evidência | Resultado |
| --- | --- | --- |
| Contratos da ponte | `python -m unittest discover -s scripts -p test_production_app_compose_bridge.py` | 34 testes: 33 passaram e 1 symlink real indisponível no Windows; guarda de symlink também passou por fixture independente |
| Fronteiras cobertas | rejeição de argumentos antes do Docker, non-root, paths/symlinks/hard links/metadados, duplicatas de ambiente, segredo sentinela, fontes por serviço, defaults/imagem, deriva de ambiente/rede/mount/segurança, checksum/cópia adulterada, release/rollback só API/web, arquivo Git limitado e pin do helper | Passou com dados sintéticos, sem Docker real/SSH |
| Regressões de release | cinco `ReleaseContracts`: inventário sem escrita, app→web, flag facial falsa antes do build, web→app→rollback, falha de build/saúde com recuperação | 5 passaram em 388,813 s; fronteiras Docker/Git/HTTP simuladas |
| Ruff da ponte e scripts de coordenação | `python -m ruff check` nos arquivos da ponte, teste, estado, política de workflow e web | Passou |
| Ruff do teste de escopo | `python -m ruff check --select F,E9 scripts/test_prod_app_release_scope.py` | Passou; dois FURB192 preexistentes em linhas não alteradas ficam fora do gate CI desse arquivo |
| Política web existente | `python scripts/test_deploy_prod_web_policy.py` | Passou com identidade semântica app e contrato web-only preservado |
| Sintaxe | Git Bash `-n` no executor app e instalador | Passou |
| OpenSpec | `openspec validate add-root-only-compose-release-bridge --strict` | Passou após separar o requisito semântico |
| Shell final com pins atualizados | Git Bash `scripts/test_deploy_prod_app_services.sh` | 6 testes passaram em 222,466 s; política shell passou |
| Escopo | `python scripts/test_prod_app_release_scope.py` | 23 passaram em 231,954 s |
| Classificador | `python scripts/test_classify_prod_release.py` | 16 passaram em 4,447 s |
| Workflow protegido | `python scripts/test_production_release_workflow_policy.py` | Passou; candidato API/web elegível, dispatch protegido e pins exatos |
| Segredos | Gitleaks 8.24.3 `stdin --redact` sobre `git diff --cached` do conjunto explícito de 20 arquivos | Nenhum segredo encontrado em 164.521 bytes; artefato preexistente `output` excluído |

## Push e CI da branch

- O primeiro commit enviado foi `ff735dfa35a3334c6208de46bf774c56f17df623`. A revisão adicionou recusas para aliases de rede inexplicados, prioridade de gateway e opção `NoCopy` de volume, recalculou os pins e foi publicada no commit `94662062f7f2dffd9df78714c305035e7dbbbdf7` (`fix(ops): prove network and volume options before release`).
- O CI do commit inicial (`44306467902`) foi cancelado depois que o commit corrigido iniciou uma validação integral sobreposta; ele foi substituído pelo run mais novo, não por uma falha.
- O run [44307098266](https://github.com/conradodeita/markina-gallery/actions/runs/44307098266), no SHA `94662062f7f2dffd9df78714c305035e7dbbbdf7`, terminou com sucesso em 18/11/2026. Passaram `gitleaks`, `openspec`, classificação de escopo, frontend, qualidade e três partições do backend, gate agregado do backend, imagens AMD64/ARM64, inventário de homologação e todos os demais jobs aplicáveis; o contexto `gemma-runtime` legado também ficou verde.
- O workflow foi disparado com `operation=none`. Instalação protegida, preflight e release/deploy foram pulados; nenhum container ou serviço de produção foi alterado por essa rodada.
- Escopo/segredos e diff foram revisados antes dos commits. Nenhum arquivo de aplicação, migration, credencial ou ambiente entrou no delta; o caminho preexistente `output` permaneceu fora do escopo.
- Task 4.1 concluída com gates locais e CI integral verde neste SHA. A próxima etapa é abrir o PR, acompanhar os checks de PR e integrar somente quando os seis contextos exigidos pela proteção estrita de `main` passarem.
- Instalar a ponte e o wrapper apenas pelo dispatch protegido depois da integração. O preflight real ainda pode recusar campos de runtime sem contrato comprovado; uma recusa não deve ser convertida em aprovação automática.
- CI pós-merge `44316971108` no SHA integrado `cf63a0d7e3cc0b6cd0c81af813bdca972c62aaff`: qualidade, frontend, imagens, backend (três shards e agregado), OpenSpec, escopo, inventário e Gitleaks passaram. O job read-only `production-app-preflight` recusou com `production-preflight: script diverge do blob revisado`; não houve build nem alteração de produção.
- Dispatch protegido de instalação `44317813361`, no mesmo SHA, passou todos os gates e recebeu a aprovação do ambiente já autorizada. O instalador parou em `origin_invalid`, antes de `sudo`, lock, escrita ou consulta Docker. A URL remota sanitizada do checkout é `ssh://github.com/conradodeita/markina-gallery.git`; o instalador atual aceitava somente HTTPS. Nenhum container, fonte, recibo ou configuração Git foi modificado.
- A CI pós-merge `44329800852`, no SHA `128f0d9e61e2aedc7921a33578105de68e65477b`, passou nos gates de código e falhou somente no preflight read-only com `production-preflight: script diverge do blob revisado`; nenhum build ou deploy ocorreu.
- O dispatch protegido `44329904087` teve os gates de código verdes e recebeu a aprovação autorizada do ambiente `production`, mas parou em `origin_invalid` antes de `sudo`, lock, escrita ou consulta Docker. Nenhum container, fonte, recibo, permissão ou configuração Git foi alterado.
- Diagnóstico SSH somente-leitura classifica `origin` como `git@github.com:conradodeita/markina-gallery.git`; `origin/main` corresponde ao SHA integrado `128f0d9e61e2aedc7921a33578105de68e65477b`, checkout é `bfe511f850224823254b0fc9f51fa7ff60ecfba0` e está limpo. A leitura anterior havia reportado URI SSH; a checagem atual do valor configurado e do valor efetivo confirma a forma SCP exata, que faltava na allowlist.
- O follow-up, baseado diretamente em `main`, aceita somente essa terceira forma SSH exata além de HTTPS e URI SSH, sem reescrever `origin`. Localmente passaram `34` testes, com `1` skip de symlink real no Windows, Ruff, Bash `-n`, OpenSpec estrito e `git diff --check`. Task 2.4 está concluída; task 5.1 também foi concluída após a instalação protegida. Tasks 4.2 e 5.2 continuam abertas.

## Retry de release — propriedade privada dos snapshots

- O workflow `44357612611` no SHA `45f4408de5d9149aaf033e18d296d17f600d84a9` passou os gates de código, incluindo os três shards do backend. O escopo do preflight passou; o inventário read-only encerrou com `snapshot_file_permissions_invalid` antes de emitir fingerprint. O job mutável de produção não iniciou.
- Diagnóstico SSH estritamente read-only consultou labels Docker de API/web e metadados `stat`, sem abrir conteúdo dos snapshots. A fonte API é `root:root 0600`, com diretórios `root:root 0700`; as duas fontes web e seus diretórios são `ubuntu:ubuntu 0600/0700`. O UID `1001` pertence a `ubuntu` e coincide com o owner do checkout. `deploy-state` também é privado `ubuntu:ubuntu 0700`.
- Causa: `_validate_snapshot_source` exigia owner root para arquivos sob `deploy-state` e owner root em todos os diretórios descendentes, incompatível com a árvore privada preexistente do usuário do checkout. As fontes não foram alteradas, nenhum serviço foi recriado e nenhum segredo/configuração foi lido.
- A implementação local da tarefa 2.5 permite somente `root` ou o owner do checkout em árvore sem bits de acesso para grupo/outros; arquivos precisam ser regulares, legíveis, não executáveis e sem hard links. Cópias persistentes permanecem `root:root` root-only. O primeiro teste detectou pins antigos do helper e do executor; ambos foram recalculados. Na repetição passaram 37 testes da ponte (36 passaram, 1 skip de symlink real indisponível no Windows), Ruff, Bash `-n`, 23 testes de escopo, política do workflow, 6 contratos shell (219,093 s), OpenSpec estrito e `git diff --check`.
- O binário Gitleaks não está disponível neste Windows; a revisão manual não encontrou segredos no delta e o gate Gitleaks obrigatório será executado no CI remoto antes do merge. CI da branch/PR e novo preflight protegido permanecem pendentes; a task 2.5 não está marcada como concluída.

### Revalidação consolidada da adoção — 19/11/2026

- A suíte de adoção executada em Linux isolado passou: 18 testes (17 passaram; 1 teste opt-in de compatibilidade com Engine foi pulado nesta suíte). A compatibilidade com Docker Desktop Engine 29.9.3/Compose 5.6.1 já havia passado em execução separada; o código de tradução não mudou desde essa execução. Os testes cobrem tradução API/web, segredos sentinela, modos inválidos, prova independente, registros privados, adulteração, transição e recuperação parcial.
- A suíte anterior da ponte passou em Linux isolado: 37/37. A suíte longa do executor passou: 7/7 em 414,020 s, incluindo ordem API/web e falhas com preservação de recuperação; a política API/web também passou. A suíte de escopo passou: 26/26 em 266,134 s. Os 10 testes do verificador CI passaram.
- Ruff passou nos sete arquivos Python alterados. Sintaxe Bash do executor e wrapper passou no Git Bash. `git diff --check` passou. OpenSpec estrito passou para `add-root-only-compose-release-bridge` e `add-production-app-release-workflow`. YAML do workflow de adoção foi parseado com PyYAML e os três jobs esperados foram encontrados.
- Políticas da release e do workflow protegido passaram; a política reportou `publication_candidate_ready=true / somente_api_web`. Os pins conferem com os blobs Git normalizados atuais: helper `7fc38475272e26719c0c3d0d032d56056848ee3e` e executor `2c486faf53bfb5cb8d345789c7701d372766974d`.
- Gitleaks 8.24.3, em container local sem rede e sem volumes nomeados, varreu os arquivos alterados e novos copiados para `work/gitleaks-scan-20261119`: 434.115 bytes, nenhum segredo encontrado. O CI continua responsável pela varredura completa do histórico após o push.
- Nenhuma instalação, adoção persistente, alteração de configuração/credenciais ou deploy foi executado. A revisão do diff local não encontrou arquivo fora do escopo; `work/` é material local de validação e permanece fora do conjunto de publicação. CI de PR e revisão humana ainda são pendentes.


## Integração, instalação e diagnóstico aprovados — 19/11/2026

- PR #387: CI 44580110183 verde no SHA 4e701edde0a46e918cb22e8c77c421d87c31994a; revisão humana aprovada e merge em 850fce2481329929965971a3a03bb70380ce6440. CI main 44594737182 terminou com todos os gates de código verdes e falha isolada do preflight: `production-preflight: script diverge do blob revisado`. O verificador do workflow protegido comprovou essa condição antes da instalação.
- Proprietário autorizou explicitamente instalar somente ponte/wrapper e executar diagnóstico read-only, após inventário: clearbudget-vnic, checkout limpo bfe511f850224823254b0fc9f51fa7ff60ecfba0, API/web saudáveis, entrada Markina 127.0.0.1:8080 e https://markina.pickyourpic.com.br. Não autorizou persistência da base nem deploy nesta aprovação.
- Workflow de instalação 44598751064 passou no SHA integrado. Helper root:root 0755, blob 7fc38475272e26719c0c3d0d032d56056848ee3e, SHA-256 7c0308bb629630d0b92606fc252743a74e123aea294ce4b7d3eb55f2f3a5c358; wrapper root:root 0755, SHA-256 c2ff05b8c28ebbaf038a340a2afc4fcfa5aaac5034f32e3b8cecf8ec8f56ec12. Conferência SSH independente confirmou metadados e hashes.
- Recuperação dos executores: /var/backups/markina-gallery/app-compose-bridge-20261119T192952Z-850fce248132 e /var/backups/markina-gallery/preflight-ssh-wrapper-20261119T192954Z-preview-migration-850fce248132. O instalador conferiu backups e containers_unchanged=true. Checkout ativo permaneceu bfe511f, limpo; somente origin/main avançou para o SHA de suporte. API/web e demais serviços Markina permaneceram saudáveis; recursos dos projetos vizinhos não foram alterados.
- Diagnóstico protegido 44599017603 passou no SHA 850fce2481329929965971a3a03bb70380ce6440: adoption_status=ready; adoption_fingerprint=48347d4edb1ff4dc450f3162bc3c8a5e299383c237b3bcf729550bf51abc996e. Saída confirmou impacto read-only; persist-runtime-adoption ficou pulado. Nenhum modelo privado ou valor TOTP foi emitido.
- Próxima operação proposta (task 6.9): workflow manual de adoção, operation=adopt, no mesmo SHA e fingerprint; repetir CI/prova/saúde/schema sob lock e persistir somente modelos/manifesto e cópias históricas na raiz fixa /var/lib/markina-gallery/app-compose-bridge (diretórios 0700, arquivos 0600, root:root), ativando registro atomicamente. Preservar fontes e registro anterior; sem recriar containers, editar .env/credenciais, migrations ou alterar serviços vizinhos. Divergência de fingerprint bloqueia a operação; falha antes da ativação preserva a base anterior. Depois, repetir preflight normal. Aprovação de adoção não aprova deploy; upload de artifact continua dependência separada.
- Estas evidências documentais ficam no worktree até o checkpoint de publicação seguinte para preservar o SHA/fingerprint operacional apresentado e evitar novo CI completo apenas por atualização de status.


## Adoção persistente e preflight normal — 19/11/2026

- Proprietário autorizou explicitamente persistir a base para o fingerprint de adoção 48347d4edb1ff4dc450f3162bc3c8a5e299383c237b3bcf729550bf51abc996e e repetir o preflight. Workflow protegido 44600949150 passou nos três jobs; SHA 850fce2481329929965971a3a03bb70380ce6440. Não houve deploy.
- Conferência independente antes/depois, somente hashes e identidades em work/adoption-before.json e work/adoption-after.json: todos os containers do host (IDs, imagens, início e digest de Config/HostConfig/Mounts/NetworkSettings) iguais; hashes das fontes históricas e docker/.env.homolog iguais. O cálculo inicial de saúde incluiu containers históricos parados, portanto seu booleano agregado não representa os serviços ativos. Conferência de docker ps confirmou os 13 serviços Markina ativos saudáveis; preflight confirmou API/web individualmente. Registro active-base.json pertence a root:root, modo 0600; helper validou modelos e manifesto privados.
- Preflight normal executado via wrapper pinado, SSH_ORIGINAL_COMMAND=MARKINA_APP_TARGET_SHA=850fce2481329929965971a3a03bb70380ce6440, passou: schema 20261113_0126, APP_ENV=production, FACIAL_PROCESSING_ENABLED=true; API/web healthy, nginx em 127.0.0.1:8080, healthz/api-health/web HTTPS 200; fingerprint de release 39890eb4d897c059e851c59ef8a5e94dce8209d9aa91a0b99388e83ce8b29a4b. Fontes e modelo adotado foram provados pelo fluxo normal, sem exceção de recuperação.
- Retentativa somente dos jobs falhos/dependentes do CI main 44594737182 disparada para registrar preflight no GitHub e preparar o mesmo bundle sem repetir os gates de código aprovados. Acompanhar resultado; o job production continua sujeito a aprovação de release própria. Task 4.5 do release e 5.4 da otimização ainda dependem de autorização explícita para nova chave/authorized_keys/secret de upload; inventário confirmou wrapper e chave ausentes no host e secret ausente no Environment production. A autorização foi solicitada para essa operação distinta; não modificar credenciais antes dela.


### Candidato de release pronto, sem publicação

Retentativa 2 do CI main 44594737182: production-app-preflight e production-app-image-artifact passaram; shards/gates de código verdes da tentativa anterior foram reutilizados. Fingerprint de release confirmado no GitHub: 39890eb4d897c059e851c59ef8a5e94dce8209d9aa91a0b99388e83ce8b29a4b. Bundle ARM64 do SHA 850fce2481329929965971a3a03bb70380ce6440: SHA-256 a37a294d0683ac126be2beb51b5d66c41e0c32698b8145244ebab967feab72d3; artifact production-app-arm64-850fce2481329929965971a3a03bb70380ce6440 disponível no mesmo run. Job production-app-release aguarda aprovação production; não foi aprovado nem executado. A fila depende da credencial exclusiva de upload (autorização específica solicitada e ainda pendente). Não repetir build/CI enquanto o artifact válido do run continuar disponível. Só marcar release após prova de versão/saúde/schema/HTTPS e preservação facial/serviços vizinhos.
